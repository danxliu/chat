def finish(continue_task: bool, summary: str) -> str:
    """
    Finishes the current agent execution.
    
    Args:
        continue_task (bool): If True, indicates the task is not complete and needs to continue in a new context. If False, the task is completely finished.
        summary (str): A summary of the current task and a list of steps that have been taken in chronological order.
    """
    if continue_task:
        return f"Task context saved. Ending current execution loop to continue in a new context. Summary: {summary}"
    
    return f"Task completed. Summary: {summary}"
