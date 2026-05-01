from agent import get_agent


def main():
    print("Initializing Agent...")
    agent = get_agent()

    query = "Hello! Can you confirm you are connected?"
    print(f"\nSending Query: '{query}'")

    response = agent.chat(query)

    print("\nFinal Response:")
    print(str(response))


if __name__ == "__main__":
    main()
