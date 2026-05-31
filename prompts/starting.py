IMPORTANT_INSTRUCTIONS = """
# SYSTEM INSTRUCTIONS & CONSTRAINTS
- **COMPLETION:** When you have completed the task, you MUST provide a complete and detailed response to the user's original request in your message.
- **Up-to-Date Information:** Your training data is not current. For any information regarding current events, real-time data, or specific details that might have changed recently, you MUST utilize the available tools (e.g., web search, finance) to retrieve the most current and accurate information.
- **Environment:**
    - Date: {{ current_date }}
    - Work Directory: {{ work_dir }}
    - Process PID: {{ current_pid }} (DO NOT terminate this process)
"""

STARTING_PROMPT_TEMPLATE = IMPORTANT_INSTRUCTIONS + "\n\n# USER REQUEST\n{{ query }}"
