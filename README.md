# RAG QA Agent

## Overview
A Question Answering agent built using Retrieval-Augmented Generation (RAG). 
The agent retrieves relevant context from a knowledge base and generates 
accurate answers using an LLM.

## Project Structure
- main.py          → entry point of the application
- rag_agent.py     → core RAG logic
- data.txt         → knowledge base data
- pyproject.toml   → project dependencies

## Setup
1. Clone the repo
2. Run: uv sync
3. Create a .env file and add your API keys

## How to Run
python main.py

## Tech Stack
- Python
- ChromaDB (vector store)

## Status
- [x] RAG application complete
- [ ] Evaluation in progress