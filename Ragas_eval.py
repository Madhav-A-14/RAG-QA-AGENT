import asyncio
from openai import AsyncOpenAI
from Rag_Test import RAGEvaluator 

from ragas.llms import llm_factory
from ragas.embeddings.base import embedding_factory
from ragas.metrics.collections import(
    Faithfulness,
    ContextPrecision,
    ContextRecall,
    AnswerRelevancy,
    FactualCorrectness,
)

class RagasEvaluator:
    """
     Uses the same testcases generated in Deepteam code.
    """
    
    def __init__(self, test_cases:list, model_name: str = "gpt-5-nano"):
        self.test_cases = test_cases
        self.results = {}
        
        client = AsyncOpenAI()
        self.llm = llm_factory(
            model_name,
            client = client,
            max_tokens = 8192,
        )
        self.embeddings = embedding_factory(
            "openai", model="text-embedding-3-small", client=client
        )
        
    
    # Definig Ragas Metrics
    
    def build_metrics(self) -> dict :
        return{
            "Context_Precision" : ContextPrecision(llm = self.llm),
            "Context_Recall" : ContextRecall(llm = self.llm),
            "Faithfullness" : Faithfulness(llm = self.llm),
            "Factual_Correctness" : FactualCorrectness(llm = self.llm),
            "Answer_Relevancy" : AnswerRelevancy(llm = self.llm,embeddings=self.embeddings)
        }
        
        
    async def _scoring(self, name: str, metric, case) -> float:
        if name == "Context_Precision":
            result = await metric.ascore(
                user_input=case.input,
                reference=case.expected_output,
                retrieved_contexts=case.retrieval_context,
            )
        elif name == "Context_Recall":
            result = await metric.ascore(
                user_input=case.input,
                retrieved_contexts=case.retrieval_context,
                reference=case.expected_output,
            )
        elif name == "Faithfullness":
            result = await metric.ascore(
                user_input=case.input,
                response=case.actual_output,
                retrieved_contexts=case.retrieval_context,
            )
        elif name == "Factual_Correctness":
            result = await metric.ascore(
                response=case.actual_output,
                reference=case.expected_output,
            )
        elif name == "Answer_Relevancy":
            result = await metric.ascore(
                user_input=case.input,
                response=case.actual_output,
                
            )
        else:
            raise ValueError(f"Unknown Metric: {name}")

        return result.value
    
    # Run Ragas Evaluation
    
    async def run_evaluation(self):
        
        metric_map = self.build_metrics()
        self.results = {name: [] for name in metric_map}
        
        for i, case in enumerate(self.test_cases,1):
            print(f"\n[Ragas] Evaluating test case {i}/{len(self.test_cases)}...")
            for name, metic in metric_map.items():
                score = await self._scoring(name,metic,case)
                self.results[name].append(score)
    
    
    # This function runs the scoring part and stores the results.
    def run_ragas(self):
        asyncio.run(self.run_evaluation())
        
    # Print Results 
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
        self.run_ragas()
        self.print_results()
        


# ENTRY POINT
        
if __name__ == "__main__":
        
    # Calling RAGEvaluator to use already built testcases.
    deepeval = RAGEvaluator()
    deepeval.load_or_generate_dataset()
    deepeval.build_test_cases()
    
    
    ragas = RagasEvaluator(deepeval.test_cases)
    ragas.run()
    
    