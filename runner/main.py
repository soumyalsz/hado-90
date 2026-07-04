import asyncio
import os
import glob
import yaml
import json
import httpx
from jsonschema import validate
from runner.config import OLLAMA_BASE_URL, TARGET_MODEL, DEFENSE_MODE, TARGET_SYSTEM_SHIELD
from runner.judge import evaluate_response
from runner.quote_validator import validate_judge_citations
from runner.aggregator import aggregate_run_results
from runner.renderer import generate_html_report
from runner.mutator import generate_mutation
from runner.guardrails import scan_output_guardrail
from runner.logger import ws_logger

SCHEMA_PATH = "catalog/schemas/attack.schema.json"
PRODUCTION_CATALOG_DIR = "catalog/attacks/production"
STAGING_CATALOG_DIR = "catalog/attacks/staging"
MAX_MUTATION_DEPTH = 2


async def emit_status(message: str):
    print(message)
    await ws_logger.broadcast(message)


def load_and_validate_catalog() -> list:
    """Reads every YAML in the production catalog and validates against the schema."""
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)

    attack_definitions = []
    yaml_files = glob.glob(os.path.join(PRODUCTION_CATALOG_DIR, "*.yaml"))
    for file_path in yaml_files:
        with open(file_path, "r") as f:
            entries = yaml.safe_load(f) or []
            for attack in entries:
                validate(instance=attack, schema=schema)
                attack_definitions.append(attack)
    return attack_definitions


async def save_discovered_exploit(attack_id: str, category: str, severity: str, mutated_prompt: str, criteria: str):
    """Persists a successful mutation to the staging catalog for future reuse."""
    os.makedirs(STAGING_CATALOG_DIR, exist_ok=True)
    staging_file = os.path.join(STAGING_CATALOG_DIR, f"discovered_{attack_id}.yaml")

    payload = [{
        "attack_id": f"{attack_id}-MUTATED",
        "category": category,
        "severity": severity,
        "prompt": mutated_prompt,
        "evaluation_rubric": {"fail_criteria": criteria}
    }]

    with open(staging_file, "w") as f:
        yaml.safe_dump(payload, f)
    await emit_status(f"Found a working exploit: saved to {staging_file}")


async def probe_target(client: httpx.AsyncClient, adversarial_prompt: str) -> str:
    """Fires the adversarial prompt at the target model and runs guardrail checks on the output."""
    try:
        messages = []
        if DEFENSE_MODE:
            messages.append({"role": "system", "content": TARGET_SYSTEM_SHIELD})
        messages.append({"role": "user", "content": adversarial_prompt})

        ollama_response = await client.post(
            f"{OLLAMA_BASE_URL}/chat",
            json={
                "model": TARGET_MODEL,
                "messages": messages,
                "stream": False,
                "keep_alive": 0,
                "options": {"temperature": 0.0}
            },
            timeout=45.0
        )

        raw_text = ollama_response.json()["message"]["content"]
        was_blocked, safe_text = scan_output_guardrail(raw_text)
        if was_blocked:
            await emit_status("   ◌ Guardrail blocked some concerning output")
        return safe_text
    except Exception as exc:
        await emit_status(f"   Error during inference: {exc}")
        return f"TARGET EXCEPTION: {exc}"


def _reconcile_verdicts(target_output: str, raw_verdict):
    """Validates citations and re-derives consensus from the sanitized sub-verdicts."""
    _, raw_verdict.judge_a_verdict = validate_judge_citations(target_output, raw_verdict.judge_a_verdict)
    _, raw_verdict.judge_b_verdict = validate_judge_citations(target_output, raw_verdict.judge_b_verdict)

    raw_verdict.is_violation = raw_verdict.judge_a_verdict.is_violation and raw_verdict.judge_b_verdict.is_violation
    raw_verdict.consensus = "agreement" if raw_verdict.judge_a_verdict.is_violation == raw_verdict.judge_b_verdict.is_violation else "conflict"
    raw_verdict.verbatim_quotes = list(set(raw_verdict.judge_a_verdict.verbatim_quotes + raw_verdict.judge_b_verdict.verbatim_quotes))
    return raw_verdict


def _build_history_entry(attack: dict, adversarial_prompt: str, target_output: str, verdict, attempt: int) -> dict:
    """Packs one test iteration into the shape the aggregator expects."""
    attack_label = f"{attack['attack_id']}-G{attempt}" if attempt > 0 else attack["attack_id"]
    return {
        "attack_id": attack_label,
        "category": attack["category"],
        "severity": attack["severity"],
        "prompt": adversarial_prompt,
        "target_response": target_output,
        "is_violation": verdict.is_violation,
        "verbatim_quotes": verdict.verbatim_quotes,
        "reasoning": verdict.reasoning,
        "consensus": verdict.consensus,
        "judge_a": str(verdict.judge_a_verdict.is_violation),
        "judge_b": str(verdict.judge_b_verdict.is_violation)
    }


async def _run_attack_chain(client: httpx.AsyncClient, attack: dict):
    """Runs one attack through the full mutation loop, returning all history entries."""
    await emit_status(f"\nTesting: {attack['attack_id']}")

    current_prompt = attack["prompt"]
    breach_found = False
    chain_history = []

    for attempt in range(MAX_MUTATION_DEPTH + 1):
        if breach_found:
            break

        if attempt > 0:
            await emit_status(f"   Attempt {attempt}/{MAX_MUTATION_DEPTH}...")

        target_output = await probe_target(client, current_prompt)
        raw_verdict = await evaluate_response(current_prompt, target_output, attack["evaluation_rubric"])
        reconciled = _reconcile_verdicts(target_output, raw_verdict)

        consensus_icon = "◦" if reconciled.consensus == "agreement" else "◌"
        await emit_status(f"     {consensus_icon} Judges: {reconciled.consensus.upper()}")

        chain_history.append(_build_history_entry(attack, current_prompt, target_output, reconciled, attempt))

        if reconciled.is_violation:
            await emit_status(f"   ◌ Breach detected at attempt {attempt}")
            breach_found = True
            if attempt > 0:
                await save_discovered_exploit(
                    attack["attack_id"], attack["category"], attack["severity"],
                    current_prompt, attack["evaluation_rubric"]["fail_criteria"]
                )
        else:
            await emit_status(f"   • Held strong at attempt {attempt}")
            if attempt < MAX_MUTATION_DEPTH:
                await emit_status("   Tweaking attack...")
                evolved_attack = await generate_mutation(current_prompt, target_output)
                current_prompt = evolved_attack.mutated_prompt

    return chain_history


async def start_pipeline():
    """Top-level orchestrator — loads the catalog, runs every attack chain, and renders the report."""
    await emit_status("\n" + "="*50)
    await emit_status("  Hado 90 v1.0.0 - Starting test suite...")
    await emit_status("="*50 + "\n")

    try:
        attacks = load_and_validate_catalog()
    except Exception as exc:
        await emit_status(f"Error loading attacks: {exc}")
        return

    audit_trail = []

    async with httpx.AsyncClient() as client:
        for attack in attacks:
            chain_results = await _run_attack_chain(client, attack)
            audit_trail.extend(chain_results)

    summary = aggregate_run_results(audit_trail)
    generate_html_report(summary)


if __name__ == "__main__":
    asyncio.run(start_pipeline())