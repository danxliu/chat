from ddgs import DDGS


def search_books(query: str, max_results: int = 5) -> str:
    """
    Searches for books matching the query.

    Use this when the user asks for book recommendations, information
    about specific books, or book-related queries. Returns title,
    author, description, and purchase links.

    Args:
        query (str): The search query for books.
        max_results (int): Max results (1-20, default 5).
    """
    try:
        max_results = max(1, min(max_results, 20))
        results = list(DDGS().books(query, max_results=max_results))
        if not results:
            return "No book results found."

        md = ["### Book Search Results:"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No Title")
            author = r.get("author", "Unknown")
            description = r.get("description", "")
            url = r.get("url", "")
            rating = r.get("rating")
            price = r.get("price", "")
            image = r.get("image", "")

            md.append(f"{i}. **{title}**")
            if author:
                md.append(f"   ✍️ {author}")
            if rating is not None:
                md.append(f"   ⭐ {rating}")
            if price:
                md.append(f"   💰 {price}")
            if description:
                md.append(f"   _{description}_")
            if image:
                md.append(f"   ![Cover]({image})")
            if url:
                md.append(f"   🔗 [{url}]({url})")

        return "\n\n".join(md)
    except Exception as e:
        return f"Error during book search: {e}"
