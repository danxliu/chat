IMPORTANT_INSTRUCTIONS = """
# SYSTEM INSTRUCTIONS & CONSTRAINTS
- **CRITICAL:** If you reach step {{ step_threshold }}, or if you are at risk of running out of context/steps before completion, you MUST immediately call:
  `finish(continue_task=True, summary="<detailed_chronological_summary_with_code_snippets>")`
- **COMPLETION:** When you have completed the task, you MUST provide a complete and detailed response to the user's original request in your message. Do NOT just put the result in the `finish` tool summary. Once you have provided the final response, call:
  `finish(continue_task=False, summary="<brief_summary>")`
- **Environment:**
    - Date: {{ current_date }}
    - Work Directory: {{ work_dir }}
    - Process PID: {{ current_pid }} (DO NOT terminate this process)
"""

STARTING_PROMPT_TEMPLATE = IMPORTANT_INSTRUCTIONS + "\n\n# USER REQUEST\n{{ query }}"
