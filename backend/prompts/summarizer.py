TITLE_SUMMARIZER_PROMPT_TEMPLATE = """
Summarize the user query into a concise, catchy chat title.
- It MUST be between 3 to 5 words long.
- Output ONLY the title.
- NO quotes, NO punctuation at the end, and NO introductory text.

Examples:
Query: "Can you help me find a good recipe for a gluten-free chocolate cake?"
Title: Gluten-Free Chocolate Cake Recipe

Query: "What is the capital of Australia and how many people live there?"
Title: Australia Capital and Population

Query: "Write a python script to scrape data from a website"
Title: Python Web Scraping Script

Query: "{query}"
Title:
"""
