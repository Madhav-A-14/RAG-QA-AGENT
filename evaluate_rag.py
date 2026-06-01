import os
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

import json
from rag_agent import RAGAgent 

from deepeval import evaluate as deepeval_evaluate
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.dataset import EvaluationDataset
from deepeval.synthesizer import Synthesizer
from deepeval.metrics import(
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    GEval,
)





# ── 1. Boot your RAG Agent ────────────────────────────────────────────────────

document_paths = ["data.txt"]
chroma_dir = "chroma_store_" + "_".join([path.replace(".txt", "") for path in document_paths])
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


# ── 3. Running the Agent and Collecting TestCases ────────────────────

print("\n" + "=" * 60)
print("Running RAG on All Goldens Generated...")
print("\n" + "=" * 60)

test_cases = []

for i, golden in enumerate(dataset.goldens,1):
    query = golden.input
    expected = golden.expected_output
    
    # Retrieving relevant chunks from ChromaDB based on Query
    retrieved_docs = agent.retrieve(query)

    # Sending the Retrieved content and the Query to LLM model to generate Answer.
    raw_response = agent.generate(query,retrieved_docs)
    
    # Parsing the generated JSON output 
    try:
        parsed = json.loads(raw_response)
        actual_output = parsed.get("answer",raw_response)
    except json.JSONDecodeError:
        actual_output = raw_response    
        
    
    
    test_cases.append(
        LLMTestCase(
            input = query,
            actual_output=actual_output,
            retrieval_context=retrieved_docs,
            expected_output=expected,
        )
    )
print(f"\n✅ All {len(test_cases)} test cases built.\n")


# ── 4. Defining Generator and Retriever Metrics ────────────────────

# Retriever Metrics
relevancy = ContextualRelevancyMetric(threshold=0.7,verbose_mode=True)
recall = ContextualRecallMetric(threshold=0.7,verbose_mode=True)
precision = ContextualPrecisionMetric(threshold=0.7,verbose_mode=True)

# Generator Metrics 
answer_correctness = GEval(
    name = "Answer Correctness",
    criteria = (
        "Evaluate if the actual_output is correct and complete"
        "given the input query and retrieved context."
        "Penalise if the answer is vague, incomplete or fabricated."
    ),
    evaluation_params = [
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold= 0.7,
    verbose_mode=True
    
)

citation_accuracy = GEval(
    name = "Citation Accuracy",
    criteria = (
        "Check if the citations in the actual_output are accurate and genuinely"
        "supported by the retrieved context. Penalise hallucinated citations"
        "or citations irrelevant to the input."
    ),
    evaluation_params = [
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold= 0.7,
    verbose_mode=True
    
)

# ── 5. Running Evaluations (DeepEval) ────────────────────
# print("="*60)
# print("DEEPEVAL -- EVALUATION METRICS")
# print("="*60)
# deepeval_evaluate(test_cases,[relevancy,recall,precision])

# print("\n"+"="*60)
# print("DEEPEVAL -- GENERATOR METRICS")
# print("="*60)
# deepeval_evaluate(test_cases,[answer_correctness,citation_accuracy])

print("="*60)
print("DEEPEVAL -- RETRIEVER & GENERATOR METRICS")
print("="*60)

deepeval_metrics = [
    relevancy,
    recall,
    precision,
    answer_correctness,
    citation_accuracy
]

deepeval_evaluate(test_cases, deepeval_metrics) 



