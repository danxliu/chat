from ddgs import DDGS


def search_videos(query: str, max_results: int = 5) -> str:
    """
    Searches the web for videos matching the query.

    Use this when the user asks for video content, tutorials, clips,
    or any video-based results. Returns video URLs, thumbnails, and
    metadata.

    Args:
        query (str): The search query for videos.
        max_results (int): Max results (1-20, default 5).
    """
    try:
        max_results = max(1, min(max_results, 20))
        results = list(DDGS().videos(query, max_results=max_results))
        if not results:
            return "No video results found."

        md = ["### Video Search Results:"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            url = r.get("url", "")
            description = r.get("description", "")
            duration = r.get("duration", "?")
            publisher = r.get("publisher", "Unknown")
            published = r.get("published", "")

            # Thumbnail (images dict has various sizes)
            images = r.get("images", {})
            thumbnail = (
                images.get("large")
                or images.get("medium")
                or images.get("small")
                or images.get("image")
                or ""
            )

            md.append(
                f"{i}. **[{title}]({url})**\n"
                f"   _{publisher}_ — Duration: {duration} — {published}\n"
            )
            if thumbnail:
                md.append(f"   ![Thumbnail]({thumbnail})\n")
            md.append(f"   {description}")

        return "\n\n".join(md)
    except Exception as e:
        return f"Error during video search: {e}"
