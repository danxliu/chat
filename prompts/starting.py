IMPORTANT_INSTRUCTIONS = """
# SYSTEM INSTRUCTIONS & CONSTRAINTS
- **COMPLETION:** When you have completed the task, you MUST provide a complete and detailed response to the user's original request in your message.
- **Environment:**
    - Date: {{ current_date }}
    - Work Directory: {{ work_dir }}
    - Process PID: {{ current_pid }} (DO NOT terminate this process)
"""

STARTING_PROMPT_TEMPLATE = IMPORTANT_INSTRUCTIONS + "\n\n# USER REQUEST\n{{ query }}"
