IMPORTANT_INSTRUCTIONS = """
# SYSTEM INSTRUCTIONS & CONSTRAINTS
- **CRITICAL:** If you reach step {{ step_threshold }}, or if you are at risk of running out of context/steps before completion, you MUST immediately call:
  `finish(continue_task=True, summary="<detailed_chronological_summary_with_code_snippets>")`
- **Environment:**
    - Work Directory: {{ work_dir }}
    - Process PID: {{ current_pid }} (DO NOT terminate this process)
"""

STARTING_PROMPT_TEMPLATE = IMPORTANT_INSTRUCTIONS + "\n\n# USER REQUEST\n{{ query }}"
