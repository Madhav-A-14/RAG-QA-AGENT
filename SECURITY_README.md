# Security Testing — DeepTeam Red Teaming

## Overview
This document explains the security testing pipeline built using the
**DeepTeam** framework. It tests the RAG agent's robustness against
adversarial attacks across multiple vulnerability categories, using prompt
injection as the attack method.

File: [`security_rag.py`](./security_rag.py)

## What is being tested

**Vulnerabilities (what we're checking for):**
- **Misinformation** — `factual_errors`, `unsupported_claims`
- **Bias** — politically biased framing
- **PII Leakage** — exposing internal database structure or session data

**Attack method (how we try to break it):**
- **Prompt Injection** — adversarial inputs designed to make the agent ignore
  its grounding rules and hallucinate or leak information

## Code walkthrough

### 1. Environment setup

```python
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"
```

Disables telemetry and auto browser-opening. Must be set before any DeepEval
or DeepTeam imports, since those libraries read these variables at import
time.

### 2. The model callback

```python
async def model_callback(input: str) -> str:
    result = agent.ask(input)
    ...
```

The bridge between DeepTeam and the RAG agent. DeepTeam generates adversarial
inputs and calls this function to send them to the agent. It is defined as
an `async` function (and outside the class) because DeepTeam's red-teaming
engine runs asynchronously internally and expects a plain async callable.

### 3. The cloud-upload bypass

```python
def _noop_post(*args, **kwargs):
    print("\n[INFO] Skipping Confident AI cloud upload (not on Enterprise plan).")
```

DeepTeam automatically tries to upload risk assessment results to Confident
AI's cloud platform after every run — a feature gated behind an Enterprise
plan. Since we only need local results, this function is patched in to
replace that upload step with a no-op, preventing a crash that would
otherwise stop results from being saved locally.

### 4. Vulnerabilities and attacks

```python
def _build_vulnerabilities(self) -> list: ...
def _build_attacks(self) -> list: ...

```
Define what to test for and how to attack it. Kept as separate methods so
new vulnerability types or attack methods can be added without touching the
rest of the pipeline.

### 5. Running the test

```python
def run(self):
    with patch(
        "deepteam.red_teamer.red_teamer.RedTeamer._post_risk_assessment",
        new=_noop_post,
    ):
        risk_assessment = red_team(
            model_callback=model_callback,
            vulnerabilities=self._build_vulnerabilities(),
            attacks=self._build_attacks(),
            max_concurrent=1,
            attacks_per_vulnerability=2,
        )
```

The `patch()` context manager temporarily swaps DeepTeam's cloud-upload
method with the no-op for the duration of the `red_team()` call, then
restores it automatically afterward. Inside this block, DeepTeam:
1. Generates adversarial attack inputs
2. Sends each one to the agent via `model_callback`
3. Scores each response using an LLM-as-judge
4. Builds a `risk_assessment` object with the full results

### 6. Output
Results are printed to console (overview + detailed test cases) and saved
locally to `./security-results/`.

## How to run
```bash
python security_rag.py
```

## Code flow

    A[Set environment variables] --> B[Import agent, DeepTeam modules]
    B --> C[Define async model_callback]
    C --> D[Define _noop_post patch]
    D --> E[RAGSecurityTester.run called]
    E --> F[Patch _post_risk_assessment with _noop_post]
    F --> G[red_team executes]
    G --> H[Generate adversarial attacks]
    H --> I[Call model_callback to query agent]
    I --> J[LLM-as-judge scores each response]
    J --> K[Build risk_assessment object]
    K --> L[Print overview and test cases]
    L --> M[Save results to security-results folder]



