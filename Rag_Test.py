import os
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

import json
from config import agent,document_paths,RUN_EVALUATION,RUN_SECURITY
from report import export_report
from unittest.mock import patch


from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.dataset import EvaluationDataset,Golden
from deepeval.synthesizer import Synthesizer
from deepeval.metrics import(
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    GEval,
)
from deepteam import red_team
from deepteam.vulnerabilities import Misinformation, PIILeakage,Bias
from deepteam.attacks.single_turn import PromptInjection



# ══════════════════════════════════════════════════════════════════════════
# DEEPEVAL RAG EVALUATOR
# ══════════════════════════════════════════════════════════════════════════



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
        
        for i, golden in enumerate(list(self.dataset.goldens)[:10], 1):
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
        
        
        
# ══════════════════════════════════════════════════════════════════════════
# DEEPTEAM RAG SECURITY TESTING 
# ══════════════════════════════════════════════════════════════════════════

# ── Calling the RAG Model ─────────────────────────────────────────────────────


class RAGSecurityTester:
    
    @staticmethod
    async def model_callback(input: str) -> str:
        result = agent.ask(input)
        if isinstance(result, dict):
            return result.get("answer", str(result))
        return str(result)
    
    
    @staticmethod
    def _noop_post(*args, **kwargs):
        print("\n[INFO] Skipping Confident AI cloud upload (not on Enterprise plan).")
    
    
    
    
    
    # ── Building the necessary Vulnerabilities ─────────────────────────────────────────────────────

        # This is where we define what vulnerabilities to test for.
    
    def _build_vulnerabilities(self) -> list:
        
        return [
            Misinformation(types = ["factual_errors","unsupported_claims"]),
            PIILeakage(types=["api_and_database_access","session_leak"]),
            Bias(types = ["politics"]),
            
            
            
            # Factual_errors -> agent stating something that is not factually correct.
            # Unsupported_claims -> agent claims not backed up by retrieved corpus
            # api_and_database_access -> checks whether the agent can be tricked into exposing details that should be hidden from end users like database schema, ChromaDB details etc.
            # session_leak -> checks whether the agent can be tricked into revealing info about different user's session or previous conversation.
            # gender -> checks whether the agent makes assumptions or favor towards a particular gender.
            # politics -> tests whether the agent leans towards a political party, ideology etc while answering.
        ]
    
    # ── Setting up Attack ─────────────────────────────────────────────────────
    
        # This is where  we define "how are we trying to break it" rule.
        # PromptInjection contains sneaky instructions to make the agent ignore its grounding rules.
        
    def _build_attacks(self) -> list:
        return[
            PromptInjection(weight=2),
        ]
        
    
    # ── Running the Attack ─────────────────────────────────────────────────────
        
        # This function ties every other function together 
        
    def run(self):
        
        print("\n" + "=" * 60)
        print("--  SECURITY TEST -- ")
        print("=" * 60)
        
        with patch(
            "deepteam.red_teamer.red_teamer.RedTeamer._post_risk_assessment",
            new =RAGSecurityTester._noop_post,
        ):
            risk_assessment = red_team(
                model_callback=RAGSecurityTester.model_callback,
                vulnerabilities=self._build_vulnerabilities(),
                attacks=self._build_attacks(),
                max_concurrent=1,
                attacks_per_vulnerability_type = 2,
            )
        # Prints an overview of Risk Assessment done.
        print("\n" + "=" * 60)
        print("RISK ASSESSMENT OVERVIEW")
        print("=" * 60)
        print(risk_assessment.overview)

        # Gives a detailed report of Risk Assessment done.
        print("\n" + "=" * 60)
        print("RISK ASSESSMENT TEST CASES")
        print("=" * 60)
        print(risk_assessment.test_cases)

        
        # Saving everything to a Local Folder.
        risk_assessment.save(to="./security-results/")
        print("\nResults saved to ./security-results/")
        
        return risk_assessment
    
        








    
# ENTRY POINT
        
if __name__ == "__main__":

    run_eval     = bool(RUN_EVALUATION)
    run_security = bool(RUN_SECURITY)
    evaluator       = None
    risk_assessment = None

    if not run_eval and not run_security:
        print("Both Evaluation and Security are set to 0 in config.")

    if run_eval:
        evaluator = RAGEvaluator()
        evaluator.load_or_generate_dataset()
        evaluator.build_test_cases()
        evaluator.run_evaluation()
        evaluator.print_results()

    if run_security:
        tester = RAGSecurityTester()
        risk_assessment = tester.run()  # ← capture the return value

    if run_eval:
        export_report(
            evaluator.test_cases,
            evaluator.results,
            risk_assessment   # None if security off, populated if it ran
        )