SUMMARIZER_PROMPT_TEMPLATE = """
# Summarizer

The trajectory of the agent is stored in the file: {{ trajectory_file }}

# Instructions
- Read the trajectory file and analyze it.  The trajectory file could be large.
- Return a precise chronologically-ordered list of things the agent did
  with the reason for doing that along with relevant code snippets
"""
