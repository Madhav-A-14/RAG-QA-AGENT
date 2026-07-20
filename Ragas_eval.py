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
        self.llm = llm_factory(model_name, client = client)
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
            "Answer_Relevancy" : AnswerRelevancy(llm = self.llm,embeddings=self.e)
        }
        
        
    async def _scoring(self, name:str, metric, case) -> float:
        if name == "Context_Precision":
            result = await metric.ascore(
                query = case.input,
                expected = case.expected_output,
                retrieved = case.retrieval_context,
            )
        elif name == "Context_Recall":
            result = await metric.ascore(
                query = case.input,
                expected = case.expected_output,
                retrieved = case.retrieval_context,
            )
        elif name == "Faithfullness":
             result = await metric.ascore(
                query = case.input,
                response = case.actual_output,
                retrieved = case.retrieval_context,
            )
        elif name == "Factual_Correctness":
            result = await metric.ascore(
                query = case.input,
                response = case.actual_output,
                
            )
        elif name == "Answer_Relevancy":
            result = await metric.ascore(
                query = case.input,
                response = case.actual_output,
                
            )
        else:
            raise ValueError(f"Unknown Metric :{name}")
        
        return result.value
    
    # Run Ragas Evaluation
    
    async def run_ragas(self):
        
        metric_map = self.build_metrics()
        self.results = {name: [] for name in metric_map}
        
        for i, case in enumerate(self.test_cases,1):
            print(f"\n[Ragas] Evaluating test case {i}/{len(self.test_cases)}...")
            for name, metic in metric_map.items():
                score = await self.score_one(name,metic,case)
                self.results[name].append[score]
    