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
        
    
    
    def build_metrics(self) -> dict :
        return{
            "Context_Precision" : ContextPrecision(llm = self.llm),
            "Context_Recall" : ContextRecall(llm = self.llm),
            "Faithfullness" : Faithfulness(llm = self.llm),
            "Factual_Correctness" : FactualCorrectness(llm = self.llm),
            "Answer_Relevancy" : AnswerRelevancy(embeddings=self.e)
        }