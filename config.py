from dotenv import load_dotenv
from rag_agent import RAGAgent

load_dotenv()

document_paths = ["Theranos.txt"]
chroma_dir = "chroma_store_" + "_".join([p.replace(".txt", "") for p in document_paths])
agent = RAGAgent(document_paths, chroma_persist_dir=chroma_dir)