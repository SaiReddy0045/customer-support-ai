from graph.workflow import workflow


def main():
    print("=" * 50)
    print("ABC Technologies - AI Customer Support")
    print("Type 'exit' to quit.")
    print("=" * 50)

    while True:
        user_query = input("\nCustomer: ").strip()

        if user_query.lower() == "exit":
            print("\nThank you for using ABC Technologies Customer Support!")
            break

        state = {
            "query": user_query,
            "intent": "",
            "response": ""
        }

        result = workflow.invoke(state)

        print(f"\nDetected Intent: {result['intent']}")
        print(f"\nAI: {result['response']}")


if __name__ == "__main__":
    main()