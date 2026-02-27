"""Web search tool using Brave Search API."""

import httpx
from agent.config import Config


def web_search(query: str, count: int = 5) -> list:
    """Search the web for additional context (company pipeline, recent events, etc.)."""
    if not Config.BRAVE_API_KEY:
        return [{"error": "No BRAVE_API_KEY configured. Web search unavailable."}]

    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"X-Subscription-Token": Config.BRAVE_API_KEY, "Accept": "application/json"},
        params={"q": query, "count": count},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", [])[:count]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        })
    return results
