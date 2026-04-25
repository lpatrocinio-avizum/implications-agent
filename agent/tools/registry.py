"""Tool registry — maps tool definitions for the LLM and dispatches execution."""

import json
from agent.tools import db, fda, web

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
        "name": "resolve_drug",
        "description": "Normalize a drug name (brand, generic, or informal) to canonical identifiers using RxNorm. Returns RxCUI, generic name, brand names, ingredients, and drug class. Use this first when a news article mentions a drug to get reliable identifiers for other lookups.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Drug name as mentioned in the news (brand, generic, or informal)"}
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "get_drug_label",
        "description": "Get FDA-approved prescribing information for a drug (indications, dosing, warnings, contraindications, adverse reactions, clinical studies). Use to compare a competitor's approved label against the client's product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Brand or generic drug name (use resolve_drug first for best results)"}
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "get_adverse_events",
        "description": "Get top reported adverse events for a drug from FDA FAERS database. Use to assess a competitor's real-world safety profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Brand or generic drug name"},
                "limit": {"type": "integer", "description": "Number of top adverse reactions to return (default 10)", "default": 10},
            },
            "required": ["drug_name"],
        },
    },
    {
        "name": "get_drug_recalls",
        "description": "Check for recent FDA recalls, withdrawals, or enforcement actions on a drug. Active recalls are major competitive events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_name": {"type": "string", "description": "Brand or generic drug name"},
                "limit": {"type": "integer", "description": "Number of recent recalls to return (default 5)", "default": 5},
            },
            "required": ["drug_name"],
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
    "resolve_drug": fda.resolve_drug,
    "get_drug_label": fda.get_drug_label,
    "get_adverse_events": fda.get_adverse_events,
    "get_drug_recalls": fda.get_drug_recalls,
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
