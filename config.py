from dotenv import load_dotenv
from rag_agent import RAGAgent

load_dotenv()


# ── Run Flags ──────────────────────────────────────────────────────────────
# Set 1 to enable, 0 to disable

RUN_DEEPEVAL = 1
RUN_SECURITY   = 1
RUN_RAGAS = 1
RUN_REPORT = 1






document_paths = ["Theranos.txt"]
chroma_dir = "chroma_store_" + "_".join([p.replace(".txt", "") for p in document_paths])
agent = RAGAgent(document_paths, chroma_persist_dir=chroma_dir)