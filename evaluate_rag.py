import os
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

import json
from config import agent,document_paths
from report import export_report

from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.dataset import EvaluationDataset,Golden
from deepeval.synthesizer import Synthesizer
from deepeval.metrics import(
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    GEval,
)

class RAGEvaluator:
    def __init__(self, goldens_file:str = "goldens.json",manual_goldens_file: str = "manual_goldens.json"):
        self.document_paths = document_paths
        self.goldens_file = goldens_file
        self.manual_goldens_file = manual_goldens_file
        self.agent = agent
        self.dataset = EvaluationDataset()
        self.test_cases = []
        self.results = {}
        
    # ── Step 1: Define Manual Goldens ──────────────────────────────────────

    def _get_manual_goldens(self) -> list:
        
        with open(self.manual_goldens_file,"r")as f:
            data = json.load(f)
        return [
        Golden(input=d["input"], expected_output=d["expected_output"])
        for d in data
    ]
        
        
    # ── Step 2: Load or Generate Golden Dataset ────────────────────────────    

    def load_or_generate_dataset(self):
        if os.path.exists(self.goldens_file):
            print("\n" + "=" * 60)
            print("Loading goldens from local JSON file...")
            print("=" * 60)

            with open(self.goldens_file, "r") as f:
                data = json.load(f)

            all_goldens = [
                Golden(input=d["input"], expected_output=d["expected_output"])
                for d in data
            ]  
            self.dataset = EvaluationDataset(goldens = all_goldens)
    
            print(f"Loaded {len(all_goldens)} goldens "
            f"({sum(1 for d in data if d['source'] == 'manual')} manual, "
            f"{sum(1 for d in data if d['source'] == 'synthesized')} synthesized)")
            
        else:
            print("\n" + "=" * 60)
            print("goldens.json not found. Generating synthesized goldens...")
            print("=" * 60)  
            
            manual_goldens = self._get_manual_goldens()
            synthesizer = Synthesizer()
            synthesized_goldens = synthesizer.generate_goldens_from_docs(
                document_paths=document_paths,
                max_goldens_per_context=5, 
            )
            print(f"Synthesized {len(synthesized_goldens)} goldens.")
            
            all_goldens = manual_goldens + synthesized_goldens
            self.dataset = EvaluationDataset(goldens=all_goldens)
            
            
            
            
            
            goldens_to_save = (
            [{"input": g.input, "expected_output": g.expected_output, "source": "manual"}
            for g in manual_goldens]
            +
            [{"input": g.input, "expected_output": g.expected_output, "source": "synthesized"}
            for g in synthesized_goldens]
            )

            with open(self.goldens_file, "w") as f:
                json.dump(goldens_to_save, f, indent=2)

            print(f"\nSaved {len(goldens_to_save)} total goldens to {self.goldens_file}")
            print(f"  Manual:      {len(manual_goldens)}")
            print(f"  Synthesized: {len(synthesized_goldens)}")
            
    # ── Step 4: Build Test Cases ───────────────────────────────────────────
    
    def build_test_cases(self):
        
        print("\n" + "=" * 60)
        print("Running RAG on All Goldens Generated...")
        print("\n" + "=" * 60)
        
        for i, golden in enumerate(self.dataset.goldens,1):
            query = golden.input
            expected = golden.expected_output
    
            # Retrieving relevant chunks from ChromaDB based on Query
            retrieved_docs = agent.fetch(query)
            
            retrieval_context = [doc["content"] for doc in retrieved_docs]

            # Sending the Retrieved content and the Query to LLM model to generate Answer.
            raw_response = agent.respond(query,retrieved_docs)
        
            # Parsing the generated JSON output 
            try:
                parsed = json.loads(raw_response)
                actual_output = parsed.get("answer",raw_response)
            except json.JSONDecodeError:
                actual_output = raw_response    
            
        
        
            self.test_cases.append(
                LLMTestCase(
                    input = query,
                    actual_output=actual_output,
                    retrieval_context=retrieval_context,
                    expected_output=expected,
                    comments = raw_response
                )
            )
        print(f"\n✅ All {len(self.test_cases)} test cases built.\n")
        
        
    # ── Step 5: Define Retriever and Generator Metrics ─────────────────────────────────────────────

    def build_metrics(self)->dict:
        
        return{
            # Retiriever Metrics
            "Contextual_Relevancy":ContextualRelevancyMetric(threshold=0.7,verbose_mode=True),
            "Contextual_Recall":ContextualRecallMetric(threshold=0.7,verbose_mode=True),
            "Contextual_Precision":ContextualPrecisionMetric(threshold=0.7,verbose_mode=True),
            # Generator Metrics
            "Answer_Correctness": GEval(
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
            ),
            "Citation_Accuracy": GEval(
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
    
        }
        
    # ── Step :6 Run Evaluations ─────────────────────────────────────────────
    def run_evaluation(self):
        
        print("="*60)
        print("DEEPEVAL -- RETRIEVER & GENERATOR METRICS")
        print("="*60)
        
        metric_map = self.build_metrics()
        self.results = {}
        for name in metric_map:
            self.results[name] = []
        
        for i, test_cases in enumerate(self.test_cases,1):
            print(f"\nEvaluating test case {i}/{len(self.test_cases)}....")
            for name,metric in metric_map.items():
                metric.measure(test_cases)
                self.results[name].append(metric.score)
                
    # ── Step 7: Print Results ──────────────────────────────────────────────
    
    
    def print_results(self):
    
        print("\n" + "=" * 60)
        print("FINAL RESULTS (avg across all test cases)")
        print("=" * 60)
    
        for metric_name, scores in self.results.items():
            avg = sum(scores) / len(scores)
            status = "PASS ✅" if avg >= 0.7 else "FAIL ❌"
            print(f"{metric_name:<35} {avg:.2f}  {status}")
            
    # ── run() ties everything together ────────────────────────────────────

    def run(self):
        self.load_or_generate_dataset()
        self.build_test_cases()
        self.run_evaluation()
        self.print_results()
        export_report(self.test_cases,self.results)
    
# ENTRY POINT
        
if __name__ == "__main__":
    evaluator = RAGEvaluator()
    evaluator.run()

                    
            
