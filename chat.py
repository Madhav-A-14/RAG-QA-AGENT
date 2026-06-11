from config import agent



print("\nModel: gpt-5-nano")  

if __name__ == "__main__":   
    while True:
        query = input("\nAsk a Question (or type 'exit' to quit):  ")
        if query.lower() == "exit":
            break
        result = agent.answer(query)

        print("\nAnswer:\n", result.get("answer"))
        # print("\nCitations:",result.get("citations"))
