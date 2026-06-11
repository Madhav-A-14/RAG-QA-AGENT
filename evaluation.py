import os
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["CONFIDENT_AI_AUTO_OPEN_BROWSER"] = "NO"

import json
from config import agent,document_paths

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
    def __init__(self, goldens_file:str = "goldens.json"):
        self.document_paths = document_paths
        self.goldens_file = goldens_file
        self.agent = agent
        self.dataset = EvaluationDataset()
        self.test_cases = []
        self.results = {}
        
    # ── Step 1: Define Manual Goldens ──────────────────────────────────────

    def _manual_goldens(self) -> list:
        return[
        Golden(input="What is the NanoDrop 3000?",
            expected_output="The NanoDrop 3000 is Theranos's flagship compact portable diagnostic device capable of performing over 300 blood tests using just 1–2 microliters of capillary blood, delivering lab-grade results in under 20 minutes."),
        Golden(input="Which third-party health systems does TheraCloud integrate with?",
            expected_output="TheraCloud integrates with EPIC, Cerner, and Apple Health via HL7 and FHIR protocols."),
        Golden(input="Does the NanoDrop 3000 have full FDA approval?",
            expected_output="No. The NanoDrop 3000 is CE-marked and pending full FDA 510(k) clearance. It only received Emergency Use Approval for the COVID-19 MicroDrop Panel in 2021."),
        Golden(input="What is MicroVial Sensing?",
            expected_output="MicroVial Sensing (MVS) is Theranos's next-generation detection framework combining nanophotonic arrays and adaptive sample calibration."),
        Golden(input="When did Theranos complete its Series F and how much was raised?",
            expected_output="Theranos completed its Series F in Q1 2023, raising $240 million from Fidelity, BlackRock, and Sequoia Capital."),
        Golden(input="Can anyone use the NanoDrop Home Kit regardless of location?",
            expected_output="No. The NanoDrop Home Kit is only available in select states with licensed telehealth coverage through the TheraDirect partnership."),
        Golden(input="Who is responsible for cloud engineering at Theranos?",
            expected_output="Richard Parker is the VP of Cloud Engineering at Theranos."),
        Golden(input="Which Theranos partner handles remote care distribution?",
            expected_output="TelePath Global handles remote care distribution for Theranos."),
        Golden(input="What is the reproducibility rate of Theranos test results?",
            expected_output="Theranos test results have a reproducibility rate between 92–97% across sample types and environments."),
        Golden(input="What is the exact blood sample volume the NanoDrop 3000 uses on average?",
            expected_output="The NanoDrop 3000 uses an average sample volume of 1.2 microliters of capillary blood."),
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
            
            manual_goldens = self._manual_goldens()
            synthesizer = Synthesizer()
            synthesized_goldens = synthesizer.generate_goldens_from_docs(
                document_paths=document_paths,
                max_goldens_per_context=5, # 5 per chunk × 2 chunks ≈ 10 total
            )
            print(f"Synthesized {len(synthesized_goldens)} goldens.")
            
            all_goldens = manual_goldens + synthesized_goldens
            self.dataset = EvaluationDataset(goldens=all_goldens)
            self.save_goldens(manual_goldens,synthesized_goldens)
            
            # Saving the created Goldens
            
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
        retrieved_docs = agent.retrieve(query)

        # Sending the Retrieved content and the Query to LLM model to generate Answer.
        raw_response = agent.generate(query,retrieved_docs)
        
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
                retrieval_context=retrieved_docs,
                expected_output=expected,
            )
        )
        print(f"\n✅ All {len(self.test_cases)} test cases built.\n")
        
        
    # ── Step 5: Define Retriever and Generator Metrics ─────────────────────────────────────────────

    def _build_metrics(self)->dict:
        
        return{
            "Contextual_Relevancy":ContextualRelevancyMetric(threshold=0.7,verbose_mode=True)
            
        }

                    
            
