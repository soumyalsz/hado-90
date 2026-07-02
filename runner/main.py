import asyncio
import os
import glob
import yaml
import json
import httpx
from jsonschema import validate
from runner.config import OLLAMA_BASE_URL, TARGET_MODEL, JUDGE_MODEL
from runner.judge import evaluate_response
from runner.quote_validator import validate_judge_citations
from runner.aggregator import aggregate_run_results
from runner.renderer import generate_html_report
from runner.mutator import generate_mutation

SCHEMA_PATH = "catalog/schemas/attack.schema.json"
PRODUCTION_CATALOG_DIR = "catalog/attacks/production"
STAGING_CATALOG_DIR = "catalog/attacks/staging"
MAX_MUTATION_DEPTH = 2

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

def log_discovered_vulnerability(attack_id: str, category: str, severity: str, mutated_prompt: str, criteria: str):
    """Saves a successfully engineered mutation out to the local staging directory."""
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
    print(f"🎯 [VULNERABILITY DISCOVERED] Exploit saved cleanly to: '{staging_file}'")

async def execute_target_inference(client: httpx.AsyncClient, prompt: str) -> str:
    try:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/chat",
            json={
                "model": TARGET_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "keep_alive": 0,
                "options": {"temperature": 0.0}
            },
            timeout=45.0
        )
        return response.json()["message"]["content"]
    except Exception as e:
        return f"TARGET EXCEPTION: {str(e)}"

async def start_pipeline():
    print("=================================================")
    print("     RT-SANDBOX EVOLUTIONARY RUNNER KICKED       ")
    print("=================================================")
    
    try:
        attacks = load_and_validate_catalog()
    except Exception as e:
        print(f"❌ Catalog Schema Violation: {str(e)}")
        return

    run_history = []

    async with httpx.AsyncClient() as client:
        for attack in attacks:
            print(f"\n🔥 Processing Base Exploit: {attack['attack_id']}...")
            
            current_prompt = attack["prompt"]
            depth = 0
            breach_secured = False

            while depth <= MAX_MUTATION_DEPTH and not breach_secured:
                if depth > 0:
                    print(f"   🌀 Mutation Depth [{depth}/{MAX_MUTATION_DEPTH}] executing...")

                # 1. Fire prompt at Target
                target_out = await execute_target_inference(client, current_prompt)
                
                # 2. Grade response with Safety Judge
                raw_verdict = await evaluate_response(current_prompt, target_out, attack["evaluation_rubric"])
                
                # 3. Check citations
                _, checked_verdict = validate_judge_citations(target_out, raw_verdict)

                # Record execution details
                run_history.append({
                    "attack_id": f"{attack['attack_id']}-G{depth}" if depth > 0 else attack['attack_id'],
                    "category": attack["category"],
                    "severity": attack["severity"],
                    "prompt": current_prompt,
                    "target_response": target_out,
                    "is_violation": checked_verdict.is_violation,
                    "verbatim_quotes": checked_verdict.verbatim_quotes,
                    "reasoning": checked_verdict.reasoning
                })

                if checked_verdict.is_violation:
                    print(f"   💥 BREACH CONFIRMED at Generation {depth}!")
                    breach_secured = True
                    if depth > 0:
                        # Log it as a newly engineered exploit signature
                        log_discovered_vulnerability(
                            attack["attack_id"], attack["category"], attack["severity"],
                            current_prompt, attack["evaluation_rubric"]["fail_criteria"]
                        )
                else:
                    print(f"   🛡️ Target defended successfully at Generation {depth}.")
                    if depth < MAX_MUTATION_DEPTH:
                        print("   🧠 Activating Mutator to rewrite attack payload...")
                        mutation_res = await generate_mutation(current_prompt, target_out)
                        current_prompt = mutation_res.mutated_prompt
                    
                depth += 1

    # Compile and generate dashboard metrics
    processed_summary = aggregate_run_results(run_history)
    generate_html_report(processed_summary)

if __name__ == "__main__":
    asyncio.run(start_pipeline())