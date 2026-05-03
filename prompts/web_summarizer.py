WEB_SUMMARIZER_PROMPT = """
You are an expert content summarizer. 
Your task is to provide a concise and informative summary of the following web content.
Focus on the main points, key findings, and essential details.
Ensure the summary is easy to read and captures the core message of the original text.

CONTENT TO SUMMARIZE:
---------------------
{{ content }}
---------------------

Please provide the summary below:
"""
