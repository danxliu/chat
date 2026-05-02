def ask_user(question: str) -> str:
    """
    Asks the user a question for clarification or more information and returns their response.
    Use this tool when you are unsure about something or need additional input from the user to proceed.
    """
    print(f"\n[AGENT QUESTION] {question}")
    return input("User Response > ")
