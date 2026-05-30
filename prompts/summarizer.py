SUMMARIZER_PROMPT_TEMPLATE = """
# Summarizer

The trajectory of the agent is stored in the file: {{ trajectory_file }}

# Instructions
- Read the trajectory file and analyze it.  The trajectory file could be large.
- Return a precise chronologically-ordered list of things the agent did
  with the reason for doing that along with relevant code snippets
"""

TITLE_SUMMARIZER_PROMPT_TEMPLATE = """
Summarize the following user query into a concise, catchy chat title.
The title should be between 3 to 5 words long.
Do not use quotes or any introductory text. Just return the title itself.

User Query: {query}
"""
