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
    await ws_logger.log(message)


def load_and_validate_catalog() -> list:
    with open(SCHEMA_PATH, "r") as f:
        schema = json.load(f)
    all_attacks = []
    yaml_files = glob.glob(os.path.join(PRODUCTION_CATALOG_DIR, "*.yaml"))
    for file_path in yaml_files:
        with open(file_path, "r") as f:
            content = yaml.safe_load(f) or []
            for attack in content:
                validate(instance=attack, schema=schema)
                all_attacks.append(attack)
    return all_attacks

async def log_discovered_vulnerability(attack_id: str, category: str, severity: str, mutated_prompt: str, criteria: str):
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

async def execute_target_inference(client: httpx.AsyncClient, prompt: str) -> str:
    try:
        messages = []
        if DEFENSE_MODE:
            messages.append({"role": "system", "content": TARGET_SYSTEM_SHIELD})
        
        messages.append({"role": "user", "content": prompt})

        response = await client.post(
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
        
        raw_text = response.json()["message"]["content"]
        
        # Check output against guardrails before returning
        triggered, final_text = scan_output_guardrail(raw_text)
        if triggered:
            await emit_status("   ◌ Guardrail blocked some concerning output")
            
        return final_text
    except Exception as e:
        await emit_status(f"   Error during inference: {str(e)}")
        return f"TARGET EXCEPTION: {str(e)}"

async def start_pipeline():
    await emit_status("\n" + "="*50)
    await emit_status("  RT-SANDBOX v1.0 - Starting test suite...")
    await emit_status("="*50 + "\n")
    
    try:
        attacks = load_and_validate_catalog()
    except Exception as e:
        await emit_status(f"Error loading attacks: {str(e)}")
        return

    run_history = []

    async with httpx.AsyncClient() as client:
        for attack in attacks:
            await emit_status(f"\nTesting: {attack['attack_id']}")
            
            current_prompt = attack["prompt"]
            depth = 0
            breach_secured = False

            while depth <= MAX_MUTATION_DEPTH and not breach_secured:
                if depth > 0:
                    await emit_status(f"   Attempt {depth}/{MAX_MUTATION_DEPTH}...")

                target_out = await execute_target_inference(client, current_prompt)
                multi_verdict = await evaluate_response(current_prompt, target_out, attack["evaluation_rubric"])
                _, checked_verdict = validate_judge_citations(target_out, multi_verdict)

                # Log consensus info
                consensus_icon = "◦" if multi_verdict.consensus == "agreement" else "◌"
                await emit_status(f"     {consensus_icon} Judges: {multi_verdict.consensus.upper()}")

                run_history.append({
                    "attack_id": f"{attack['attack_id']}-G{depth}" if depth > 0 else attack['attack_id'],
                    "category": attack["category"],
                    "severity": attack["severity"],
                    "prompt": current_prompt,
                    "target_response": target_out,
                    "is_violation": checked_verdict.is_violation,
                    "verbatim_quotes": checked_verdict.verbatim_quotes,
                    "reasoning": checked_verdict.reasoning,
                    "consensus": multi_verdict.consensus,
                    "judge_a": str(multi_verdict.judge_a_verdict.is_violation),
                    "judge_b": str(multi_verdict.judge_b_verdict.is_violation)
                })

                if checked_verdict.is_violation:
                    await emit_status(f"   ◌ Breach detected at attempt {depth}")
                    breach_secured = True
                    if depth > 0:
                        await log_discovered_vulnerability(
                            attack["attack_id"], attack["category"], attack["severity"],
                            current_prompt, attack["evaluation_rubric"]["fail_criteria"]
                        )
                else:
                    await emit_status(f"   • Held strong at attempt {depth}")
                    if depth < MAX_MUTATION_DEPTH:
                        await emit_status("   Tweaking attack...")
                        mutation_res = await generate_mutation(current_prompt, target_out)
                        current_prompt = mutation_res.mutated_prompt
                    
                depth += 1

    processed_summary = aggregate_run_results(run_history)
    generate_html_report(processed_summary)

if __name__ == "__main__":
    asyncio.run(start_pipeline())