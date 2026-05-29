import json
from rag_agent import RAGAgent 

from deepeval.evaluate import evaluate as deepeval_evaluate
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.dataset import EvaluationDataset
from deepeval.synthesizer import Synthesizer





# ── 1. Boot your RAG Agent ────────────────────────────────────────────────────

document_paths = ["data.txt"]
chroma_dir = chroma_dir = "chroma_store_" + "_".join([path.replace(".txt", "") for path in document_paths])
agent = RAGAgent(document_paths,chroma_persist_dir=chroma_dir)


# ── 2. Generate Goldens (Once) or Pull from Confident AI ─────────────────────

DATASET_ALIAS = "RAG QA APPLICATION DATASET"

print("\n" + "=" * 60)
print("Loading Dataset...")
print("\n" + "=" * 60)

dataset = EvaluationDataset()

try:
    # Checking whether dataset available inorder to pull from Confident AI
    dataset.pull(alias=DATASET_ALIAS)
    print(f" Pulled {len(dataset.goldens)} from Confident AI")
    
except:
    # Dataset not available, need to generate and push to Confident AI
    print(f" Dataset not Found. Generating goldens from Data...")
    
    synthesizer = Synthesizer()
    goldens = synthesizer.generate_goldens_from_docs(document_paths = document_paths)
    
    print(f" Generated {len(goldens)} goldens.")
    print("\n Generated QA Pairs")
    
    dataset = EvaluationDataset(goldens=goldens)
    dataset.push(alias=DATASET_ALIAS)
    print(f"\n Dataset Successfully pushed into Confident AI under alias name ")


