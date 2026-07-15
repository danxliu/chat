from ddgs import DDGS


def search_images(query: str, max_results: int = 5) -> str:
    """
    Searches the web for images matching the query.

    Use this when the user asks for pictures, photos, diagrams, or any
    visual content. Returns direct image URLs you can display inline
    with markdown: ![description](image_url)

    Args:
        query (str): The search query for images.
        max_results (int): Max results (1-20, default 5).
    """
    try:
        max_results = max(1, min(max_results, 20))
        results = list(DDGS().images(query, max_results=max_results))
        if not results:
            return "No image results found."

        md = ["### Image Search Results:"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            image = r.get("image", "")
            thumbnail = r.get("thumbnail", "")
            url = r.get("url", "")
            source = r.get("source", "Unknown")
            w, h = r.get("width", "?"), r.get("height", "?")

            md.append(
                f"{i}. **{title}**\n"
                f"   - Full image: {image}\n"
                f"   - Thumbnail: {thumbnail}\n"
                f"   - Size: {w}x{h}\n"
                f"   - Source: [{source}]({url})"
            )

        md.append(
            "\n_To display an image in your response, use:_\n"
            "`![description](image_url)`"
        )
        return "\n\n".join(md)
    except Exception as e:
        return f"Error during image search: {e}"
