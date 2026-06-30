# RAG QA Agent

## Overview
A Question Answering agent built using Retrieval-Augmented Generation (RAG).
The agent retrieves relevant context from a knowledge base and generates
accurate, grounded answers using an LLM. The project also includes a full
evaluation pipeline (DeepEval) and a security testing pipeline (DeepTeam) to
measure both answer quality and robustness against adversarial attacks.

## Project Structure
- `main.py`           → entry point of the application
- `rag_agent.py`       → core RAG logic (fetch, respond, ask)
- `config.py`          → shared config module (agent instance, env vars, document paths)
- `Theranos.txt`           → knowledge base data (corpus)
- `evaluate_rag.py`    → DeepEval evaluation pipeline (`RAGEvaluator`)
- `security_rag.py`    → DeepTeam security testing pipeline (`RAGSecurityTester`)
- `report.py`          → generates color-coded Excel reports for evaluation and security results
- `manual_goldens.json`→ hand-written QA pairs used for evaluation
- `goldens.json`       → cached evaluation dataset (manual + synthesized goldens)
- `pyproject.toml`     → project dependencies

## Setup
1. Clone the repo
2. Run: `uv sync`
3. Create a `.env` file and add your API keys

## How to Run
- Run the agent: `python main.py`
- Run evaluation: `python evaluate_rag.py`
- Run security testing: `python security_rag.py`

See [`SECURITY_README.md`](./SECURITY_README.md) for a detailed breakdown of
the security testing pipeline and its flow.

## Tech Stack
- Python
- LangChain
- ChromaDB (vector store)
- OpenAI (gpt-5-nano)
- DeepEval (evaluation framework)
- DeepTeam (security / red-teaming framework, built on DeepEval)



## Status
- [x] RAG application complete
- [x] Evaluation complete
- [x] Security testing (Phase 1) complete
