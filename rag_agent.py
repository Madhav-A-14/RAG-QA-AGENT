import os 
import json
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI



json_prompt_template = """ You are a helpful assistant. Use the context below to answer the user's query. 
Format your response strictly as a JSON object with the following structure:

{{
  {{
  "answer": "<a well-formatted answer using numbered points or bullet points with each point on a new line. Use \\n between each point for clarity>",
  "citations": [
    "<relevant quoted snippet or summary from source 1>",
    "<relevant quoted snippet or summary from source 2>",
    ...
  ]
}}

Only include information that appears in the provided context. Do not make anything up.
Only respond in JSON — No explanations needed. Only use information from the context. If 
nothing relevant is found, respond with: 

{{
  "answer": "No relevant information available.",
  "citations": []
}}

Context:
{context}

Query:
{query}"""


# Load API key from .env file
load_dotenv()



class RAGAgent:            #Class Declaration
    def __init__(          #Constructor
            self,
            document_paths: list,
            embedding_model = None,
            chunk_size: int = 300,
            chunk_overlap: int = 60,
            k: int = 5,
            chroma_persist_dir: str=None,
            chroma_collection_name: str="rag_docs"
    ):
        self.document_paths = document_paths
        self.embedding_model = embedding_model or OpenAIEmbeddings()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.k = k
        self.chroma_persist_dir = chroma_persist_dir
        self.chroma_collection_name = chroma_collection_name
        self.vector_store = self._load_vector_store()
        

    # Loading and Indexing the Documents 

    def _load_vector_store(self):  
        if self.chroma_persist_dir:
            if os.path.exists(self.chroma_persist_dir) and os.listdir(self.chroma_persist_dir):
                print("\nLoading existing ChromaDB from Disk")
                return Chroma(
                    persist_directory=self.chroma_persist_dir,
                    embedding_function=self.embedding_model,
                    collection_name = self.chroma_collection_name,
                )
            print("ChromaDB not found, Creating and Saving to Disk...")
            documents = []
            for document_path in self.document_paths:
                with open(document_path, "r", encoding = "utf-8") as file:
                    raw_text = file.read()
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size = self.chunk_size,
                    chunk_overlap = self.chunk_overlap,
                )
                documents.extend(splitter.create_documents([raw_text]))
            return Chroma.from_documents(
                documents,
                self.embedding_model,
                persist_directory=self.chroma_persist_dir,
                collection_name= self.chroma_collection_name
            )
        raise ValueError("chroma_persist_dir must be provided.")
    
    # Retriever
    
    def fetch(self,query:str):
        print("Retrieving relevant chunks...")
        docs = self.vector_store.similarity_search(query,k=self.k) # stored as document object
        retrieved_docs = [doc.page_content for doc in docs]
        return retrieved_docs


    # Generator 

    def respond(
            self,
            query:str,
            retrieved_docs:list,
            llm_model = None,
            prompt_template: str = None,
    ):
        context = "\n".join(retrieved_docs)  # joining 2 strings into one
        model = llm_model or ChatOpenAI(model="gpt-5-nano")# Enabling/Setting the model 
        prompt = prompt_template or json_prompt_template# Setting the prompt template
        prompt = prompt.format(context=context,query=query)
        response = model.invoke(prompt)
        return response.content
    

    def ask(
            self,
            query:str,
            llm_model = None,
            prompt_template : str = None,
        ):

        retrieved_docs = self.fetch(query)
        generated_answer = self.respond(query,retrieved_docs,llm_model,prompt_template)
        
        try:
            res = json.loads(generated_answer)
            return res
        except json.JSONDecodeError:
            return {"error": "Invalid JSON returned from the model.","raw output":generated_answer}
            






