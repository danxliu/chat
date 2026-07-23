COMPACTION_PROMPT = """You are summarizing a conversation for context compaction. Below is an existing summary of the earlier conversation, followed by new messages that need to be incorporated. Produce an updated, concise summary that captures all key facts, decisions, and context needed to continue the conversation. Preserve specific details (names, numbers, URLs, code) that the user or assistant referenced.

=== EXISTING SUMMARY ===
{existing}

=== NEW MESSAGES TO INCORPORATE ===
{segment_text}

=== UPDATED SUMMARY ==="""
