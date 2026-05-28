from rag_agent import RAGAgent


document_paths = ["data.txt"]
chroma_dir = "chroma_store_" + "_".join([path.replace(".txt", "") for path in document_paths])
agent = RAGAgent(document_paths , chroma_persist_dir=chroma_dir)

print("\nModel: gpt-5-nano")  

while True:
    query = input("\nAsk a Question (or type 'exit' to quit):  ")
    if query.lower() == "exit":
        break
    result = agent.answer(query)

    print("\nAnswer:\n", result.get("answer"))
    # print("\nCitations:",result.get("citations"))
