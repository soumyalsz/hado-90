<p align="center">
  <img src="docs/hado 90.png" alt="Hado 90 Logo" width="200"/>
</p>

<h1 align="center">Hado 90 v1.0.0</h1>
<p align="center"><strong>Automated Local LLM Red-Teaming & Multi-Agent Consensus Framework</strong></p>

---

# Hado 90

### Automated Local LLM Red-Teaming and Multi-Agent Consensus Framework

A local-first, Ollama-powered security workstation for adversarial prompt mutation and multi-agent consensus judging. All inference is routed through a local Ollama daemon. No cloud. No telemetry. No API keys.

**Version:** v1.0.0
**Author:** [soumyalsz](https://github.com/soumyalsz)

---

Hado 90 is a local-first security workstation that automates adversarial prompt mutations against a target LLM and routes every generated response through a tribunal of independent local judge models. Their structured verdicts are reconciled, citation-verified, and aggregated into a single Safe or Compromised ruling that is forensically traceable from prompt to pixel.

The framework runs entirely on your hardware against your own models. There are no cloud gateways, no telemetry endpoints, and no third-party API keys to manage. Inference talks to a local Ollama daemon on `localhost`, and the dashboard is served by a FastAPI application you launch from source.

---

## Contents

| Section | Description |
|---------|-------------|
| [Overview](#overview) | What Hado 90 is and what it is not |
| [Workspace](#workspace) | Dashboard, terminal log, server runtime |
| [Capabilities](#capabilities) | Architectural advantage stack |
| [Engine Pipeline](#engine-pipeline) | End-to-end data transformation pathway |
| [Tech Stack](#tech-stack) | Runtime, framework, and dependency matrix |
| [Installation](#installation) | Clone, venv, dependencies, server launch |
| [Configuration](#configuration) | Environment variables and model overrides |
| [Distribution and License](#distribution-and-license) | Source-Available, Proprietary Freeware summary |
| [Threat Model and Ethics](#threat-model-and-ethics) | Authorized use only |
| [Versioning](#versioning) | v1.0.0 baseline |

---

## Overview

Hado 90 fuses two engines into one closed-loop audit cycle.

**Adversarial Mutation Engine**
A seed prompt is recursively evolved by a mutator model that returns a structured payload consisting of a rationale and a fully rewritten prompt variant. The loop runs up to a configurable maximum depth (default 2). A distinctness check rejects any candidate that is identical to the original or the prior attempt.

**Multi-Judge Consensus Engine**
Every target-model response is fanned out to two independent local judges. Each judge returns a structured verdict that is then subjected to evidence forensics: every judge-cited quote is substring-verified against the actual model output, and a verdict that cites fabricated evidence is automatically invalidated. The two sanitized verdicts are reconciled. Unanimity is required to confirm a violation.

The output of every run is a self-contained HTML workspace where each breach is traceable to the exact prompt, response, evidence quotes, and per-judge reasoning that produced the ruling.

Hado 90 is not a chatbot wrapper. It is a forensic adversarial audit console for engineers and security researchers who already know what they are testing.

---

## Engine Pipeline

The full data pathway from a schema-validated attack catalog entry to a reconciled Safe / Compromised ruling, with a recursive mutation loop on the resilient branch.

![Hado 90 engine pipeline](docs/pipeline.png)

---

## Workspace

The dashboard is a self-contained `index.html` (Tailwind CSS, dark mode) wired to a live WebSocket log stream.

### Main Dashboard

The launch console. Target model, judge roster, the launch control, and the analytics and test-case viewports populate the same page.

<!-- IMAGE_PLACEHOLDER: docs/screenshots/main-dashboard.png -->
![Hado 90 main dashboard](docs/screenshots/main-dashboard.png)

### Live Mutation Log

A streaming WebSocket terminal. Every mutation iteration, every judge cast, every verdict, and every status line is broadcast in real time to every connected dashboard session.

<!-- IMAGE_PLACEHOLDER: docs/screenshots/mutation-log.png -->
![Hado 90 live mutation log](docs/screenshots/mutation-log.png)

### Local Server Runtime

The FastAPI server boots from `python -m runner.server`, exposes the dashboard on `http://127.0.0.1:8000`, and serves a WebSocket endpoint at `/ws/logs` that the dashboard subscribes to.

<!-- IMAGE_PLACEHOLDER: docs/screenshots/server-runtime.png -->
![Hado 90 local server runtime](docs/screenshots/server-runtime.png)

---

## Capabilities

| Capability | Detail |
|------------|--------|
| Recursive prompt mutation | Loops up to `MAX_MUTATION_DEPTH` (default 2). Feeds the prior refusal back into a mutator model that returns a structured `MutationResult`. |
| Distinctness enforcement | `ensure_distinct_mutation` rejects any candidate identical to the original or the previous attempt. No idle retries. |
| Multi-judge consensus | Two independent local judges deliberate on the same prompt, response, and rubric triple. Unanimity is required to confirm a violation. |
| Citation forensics | `quote_validator` substring-verifies every judge-cited quote against the actual model output. A hallucinated citation invalidates the verdict. |
| Output guardrail sweep | `guardrails` intercepts known compromise signatures (`system compromised`, `override successful`, `security bypass confirmed`) at the transport layer before judging. |
| Local-first architecture | 100% on-device. No telemetry, no cloud gateways, no model API keys. All inference talks to a local Ollama daemon on `localhost`. |
| Auto hardware tiering | `config` sniffs VRAM via `nvidia-smi` and downshifts to a model pair that actually fits the host. No OOM crashes mid-audit. |
| Structured schemas | Pydantic contracts govern the mutator and judge I/O. No freeform JSON drift, no parsing fallbacks in production paths. |
| Schema-validated catalog | `attack.schema.json` enforces the shape of every YAML attack entry before it reaches the engine. Malformed payloads are a hard fail. |
| Exploit persistence | Successful mutations are auto-written to `catalog/attacks/staging/` for human review and re-inclusion in future suites. |
| WebSocket live telemetry | `logger` fans out every status line to every connected dashboard session in real time. No polling, no reload. |
| Forensic HTML renderer | `renderer` produces a self-contained `reports/dashboard.html` with category pass rates, finding cards, and quote-verified evidence. |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Language | Python 3.11+ | Type-annotated throughout, pyright-clean baseline |
| HTTP client | httpx (async) | Concurrent probes, structured timeouts |
| Validation | pydantic v2, jsonschema | Strict schemas for mutator, judges, attack catalog |
| Catalog format | YAML, JSON Schema | `catalog/schemas/attack.schema.json` enforces shape |
| Inference backend | Local Ollama daemon | Default `http://localhost:11434/api` |
| Backend server | FastAPI, Uvicorn | ASGI, WebSocket at `/ws/logs`, REST at `/api/run` |
| Frontend | Self-contained `index.html`, Tailwind CSS (CDN) | Pure dark mode, no build step |
| Environment | Isolated `.venv` | Configured via `pyrightconfig.json` |
| Type checking | Pyright | `pyrightconfig.json` pinned to local venv |

No cloud LLM dependencies. No outbound telemetry. The Ollama daemon is the only network endpoint Hado 90 ever speaks to, and only on `localhost`.

---

## Installation

This project is currently distributed as a source repository. There is no pre-compiled binary, no installer, and no PyInstaller bundle. You run the dashboard directly from the Python source.

### Prerequisites

- Python 3.11 or newer
- [Ollama](https://ollama.com/) installed and running locally
- At least one target model pulled (for example, `ollama pull llama3.2:1b`)
- At least two judge-capable models pulled (for example, `ollama pull llama3.1:8b` and `ollama pull qwen2.5:14b`)

### 1. Clone the Repository

```bash
git clone https://github.com/soumyalsz/hado-90.git
cd hado-90
```

### 2. Inspect the Layout

```
hado-90/
├── catalog/
│   ├── attacks/production/        YAML attack definitions (schema-validated)
│   └── schemas/attack.schema.json  JSON Schema enforcing catalog shape
├── reports/                       Generated HTML dashboards land here
├── runner/
│   ├── main.py                    Pipeline orchestrator
│   ├── server.py                  FastAPI app: /api/run, /ws/logs
│   ├── mutator.py                 Recursive prompt mutation engine
│   ├── judge.py                   Multi-judge tribunal and consensus
│   ├── quote_validator.py         Substring-verifies judge citations
│   ├── guardrails.py              Output compromise-pattern sweeper
│   ├── aggregator.py              Per-category pass-rate rollup
│   ├── renderer.py                HTML dashboard generator
│   ├── config.py                  VRAM sniffer and model selection
│   ├── logger.py                  WebSocket broadcast logger
│   └── index.html                 Dashboard UI (Tailwind, dark mode)
├── tests/                         pytest suite
├── pyrightconfig.json             pyright type-check config
├── requirements.txt               httpx, pydantic, pyyaml, jsonschema
└── .venv/                         Local virtual environment
```

### 3. Activate the Virtual Environment

The repo ships with a pre-configured `.venv`. Activate it per your platform:

```powershell
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

```bash
# Windows (Git Bash)
source .venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate
```

Install dependencies if the venv is fresh:

```bash
pip install -r requirements.txt
```

### 4. Run the Server

The dashboard is served by the FastAPI app in `runner/server.py`. The canonical entry point is the module runner:

```bash
python -m runner.server
```

The console will print something similar to:

```
INFO:     Started server process [13920]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:55008 - "WebSocket /ws/logs" [accepted]
INFO:     connection open
INFO:     127.0.0.1:49877 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:63039 - "WebSocket /ws/logs" [accepted]
INFO:     connection open
INFO:     127.0.0.1:50615 - "POST /api/run HTTP/1.1" 200 OK
```

Open the printed URL in any modern browser. The dark-mode dashboard loads, the WebSocket connects, and the terminal pane begins streaming live status lines from the audit pipeline.

### 5. Run the Tests

```bash
pytest -q
```

Open the project in VS Code with the Pylance or Pyright extension enabled and the type checker will resolve the `runner.*` package cleanly using `pyrightconfig.json`.

---

## Configuration

All runtime settings live in `runner/config.py` and are overridable through environment variables.

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434/api` | Local Ollama daemon endpoint |
| `TARGET_MODEL` | `llama3.2:1b` | Model under test |
| `JUDGE_MODEL_A` | `llama3.1:8b` | First tribunal judge |
| `JUDGE_MODEL_B` | `qwen2.5:14b` | Second tribunal judge |
| `MUTATOR_MODEL` | `llama3.2:3b` | Model that rewrites blocked prompts |
| `DEFENSE_MODE` | `False` | When `True`, the target receives a system safety prompt before each probe |

Override example:

```bash
export TARGET_MODEL="mistral:7b"
export JUDGE_MODEL_A="gemma:7b"
export JUDGE_MODEL_B="phi3:medium"
python -m runner.server
```

VRAM auto-tiering is applied through `resolve_runtime_models` when environment overrides are not provided. It uses `nvidia-smi` on Windows and Linux, `sysctl` on macOS, and `psutil` as a final fallback.

---

## Distribution and License

Hado 90 v1.0.0 is distributed under a **Source-Available, Proprietary Freeware** model. It is not open-source software. The source code is published on GitHub to make architectural review, academic evaluation, and personal learning possible, and not as an implicit license grant.

### You may

- Download, clone, and run the source code for personal, academic, and non-commercial security research.
- Read and analyze the public source tree for portfolio review, architectural study, or coursework.
- Fork the repository for private evaluation, with no public redistribution.
- Cite the project in academic work, with attribution.
- Submit bug reports and feature requests via the issue tracker.

### You may not

- Redistribute the source or any derivative of it as part of a commercial product or service.
- Re-license the code, structure, or naming under any open-source framework.
- Use the framework, the catalog, or the consensus engine outputs to train, fine-tune, or commercially evaluate third-party LLM products.
- Remove or alter the copyright, attribution, or license notices in the source tree.

### Commercial use

For commercial use, integration into commercial pipelines, or any use case not covered above, contact the author at [soumyalsz](https://github.com/soumyalsz) to discuss a separate agreement.

### No warranty

The software is provided as is, without warranty of any kind, express or implied. The authors are not liable for any claim, damages, or other liability arising from the use of the framework.

The full license instrument is bundled as `EULA.txt` in the repository root and is the controlling document for any dispute.

---

## Threat Model and Ethics

Hado 90 is built for defensive security work. It audits the alignment posture of local LLMs you own, operate, or have explicit written authorization to test.

### Use it for

- Validating the safety alignment of local models you control.
- Academic research into jailbreak taxonomy and consensus-based safety evaluation.
- Red-team exercises against your own deployments under a documented scope of work.

### Do not use it for

- Attacking third-party LLM services without explicit written authorization.
- Generating prompts, payloads, or instructions intended for harm.
- Any activity prohibited by local, national, or international law.

Every prompt, every response, every citation, and every rationale is preserved in `reports/dashboard.html`. The framework is forensically transparent by design. Use it where you can stand behind the audit trail.

---

## Versioning

| Channel | Version | Status |
|---------|---------|--------|
| Stable | v1.0.0 | Current source release |
| Source | main | Mirrors stable, tagged per release |
| Staging catalog | catalog/attacks/staging/ | Auto-populated by successful mutations. Human review required before promotion to production. |

---

Hado 90 v1.0.0. Built for local adversarial audit. Source available. Proprietary. No telemetry. No cloud.

Copyright (c) 2026 soumyalsz. All rights reserved.
