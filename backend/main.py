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

        try:
            result = workflow.invoke(state)
        except Exception:
            result = {
                "intent": "support",
                "response": "I found the relevant information, but the AI response service is temporarily unavailable. Please try again shortly."
            }

        print(f"\nDetected Intent: {result.get('intent', 'support')}")
        print(f"\nAI: {result.get('response', 'I can help with that.')}")


if __name__ == "__main__":
    main()