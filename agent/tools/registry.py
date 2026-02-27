"""Tool registry — maps tool definitions for the LLM and dispatches execution."""

import json
from agent.tools import db, web

# Tool definitions in Anthropic's tool format
TOOLS = [
    {
        "name": "get_news",
        "description": "Get the full content of a news article by its ID. Use this to read the triggering news.",
        "input_schema": {
            "type": "object",
            "properties": {
                "news_id": {"type": "integer", "description": "The news article ID"}
            },
            "required": ["news_id"],
        },
    },
    {
        "name": "search_news",
        "description": "Full-text search across all news articles. Use to find related news on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_news_for_feed",
        "description": "Search news linked to a specific feed. Use to find what this client has seen about a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "feed_id": {"type": "integer", "description": "The feed ID"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["query", "feed_id"],
        },
    },
    {
        "name": "get_newsfeed_context",
        "description": "Get the newsfeed metadata for a news+feed pair: priority, matched keywords, company, product, indication, summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "news_id": {"type": "integer", "description": "The news ID"},
                "feed_id": {"type": "integer", "description": "The feed ID"},
            },
            "required": ["news_id", "feed_id"],
        },
    },
    {
        "name": "get_alert_email",
        "description": "Get the alert email already generated for this news+feed. Contains the alert title and body.",
        "input_schema": {
            "type": "object",
            "properties": {
                "news_id": {"type": "integer", "description": "The news ID"},
                "feed_id": {"type": "integer", "description": "The feed ID"},
            },
            "required": ["news_id", "feed_id"],
        },
    },
    {
        "name": "get_recent_alerts",
        "description": "Get recent alert emails sent to this feed. Use to understand what this client has been alerted about recently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "feed_id": {"type": "integer", "description": "The feed ID"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
            },
            "required": ["feed_id"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web for additional context about a company, drug, pipeline, regulatory action, etc. Use when DB context is insufficient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "count": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
]

# Dispatch map
_TOOL_FNS = {
    "get_news": db.get_news,
    "search_news": db.search_news,
    "search_news_for_feed": db.search_news_for_feed,
    "get_newsfeed_context": db.get_newsfeed_context,
    "get_alert_email": db.get_alert_email,
    "get_recent_alerts": db.get_recent_alerts,
    "web_search": web.web_search,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name and return JSON string result."""
    fn = _TOOL_FNS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = fn(**arguments)
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})
