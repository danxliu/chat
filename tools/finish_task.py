def finish_task() -> str:
    """
    Signals that the task is completed and the agent can stop looping.
    Before calling this tool, you must ensure that you have truly answered the user's question and provided the final response in your message content.
    """
    return "Task completed."
