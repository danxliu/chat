FACT_EXTRACTION_PROMPT = """You are a memory extraction system. Analyze the following conversation exchange between a user and an AI assistant.

Extract discrete, standalone facts and preferences about the user that would be useful to remember for future conversations. Focus on:
- Personal details and preferences (name, location, job, likes/dislikes)
- Projects or tasks the user is working on
- Technical preferences (languages, frameworks, tools)
- Decisions or opinions the user expresses
- Any other lasting information

Return ONLY a JSON array of strings, each representing one fact. Each fact should be a complete sentence that stands alone without context from the conversation.
Example output: ["User works as a software engineer at Acme Corp.", "User prefers Python over JavaScript.", "User is building a stock analysis dashboard."]

If no meaningful facts are found, return an empty JSON array: []

User message: {user_msg}

Assistant response: {assistant_msg}

JSON array of facts:"""
