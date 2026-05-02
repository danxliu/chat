RESUMING_PROMPT_TEMPLATE = """
# Task Progress (Continuation {{ continuation_number }})

{{ progress_text }}

# Continue
- Complete the rest of the task.
- **DON'T** redo completed work.
- If you have been retrying the same approach without progress, step back \
and rethink the strategy from scratch.
"""
