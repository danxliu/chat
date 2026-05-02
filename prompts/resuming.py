RESUMING_PROMPT_TEMPLATE = """
# Task Progress (Continuation {{ continuation_number }})
- **Current Date:** {{ current_date }}

{{ progress_text }}

# Continue
- Complete the rest of the task.
- **DON'T** redo completed work.
- If you have been retrying the same approach without progress, step back \
and rethink the strategy from scratch.
- **COMPLETION:** When you have completed the task, you MUST provide a complete and detailed response to the user's original request in your message. Do NOT just put the result in the `finish` tool summary. Once you have provided the final response, call:
  `finish(continue_task=False, summary="<brief_summary>")`
"""
