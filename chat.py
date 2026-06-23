from config import agent



print("\nModel: gpt-5-nano")  

if __name__ == "__main__":   
    while True:
        query = input("\nAsk a Question (or type 'exit' to quit):  ")
        if query.lower() == "exit":
            break
        print()
        result = agent.ask(query)
        print(result.get("answer", "No answer returned."))
        
        citations = result.get("citations", [])
        if citations:
            print("\nCitations:")
            for c in citations:
                print(f"  Source : {c.get('source')}")
                print(f"  Lines  : {c.get('lines')}")
                print(f"  Text   : {c.get('text')}")
                print()
        else:
            print("\nCitations: None")
