# Implications Agent

An agentic competitive intelligence tool that generates strategic "Implications" sections for pharma CI alerts, powered by Claude and a PostgreSQL + Brave Search toolset.

## Overview

When a news article triggers a CI alert for a client, the Implications Agent analyzes the alert in context and produces a markdown-formatted strategic assessment answering: **"What does this news mean for *this specific client*?"**

The agent runs an autonomous tool-use loop — reading the triggering news, the pre-generated alert email, and the client's newsfeed metadata from a PostgreSQL database, searching for related news patterns, optionally performing web searches for external context, and then generating the final structured implications.

Output follows a consistent five-section format:
- **Strategic Impact** — 2-3 sentence executive summary
- **Key Implications** — 3-5 specific, actionable bullet points
- **Competitive Landscape** — how competitive dynamics shift for the client
- **Recommended Actions** — 2-3 concrete next steps
- **Context & Evidence** — sources that informed the analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        run.py  (CLI)                         │
│          python run.py --news-id 123 --feed-id 67            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             ImplicationsAgent   (agent/core.py)              │
│                                                              │
│  ┌───────────────┐   ┌──────────────────────────────────┐   │
│  │ SYSTEM_PROMPT │   │    Agentic Loop  (max N turns)    │   │
│  │ (prompts.py)  │   │                                  │   │
│  └───────┬───────┘   │  1. Send messages → Claude API   │   │
│          └───────────│  2. Claude returns tool_use       │   │
│                      │  3. Execute tools, append results │   │
│                      │  4. Repeat until text-only reply  │   │
│                      └──────────────┬───────────────────┘   │
└─────────────────────────────────────┼───────────────────────┘
                                      │
              ┌───────────────────────┼──────────────────────┐
              ▼                       ▼                       ▼
 ┌────────────────────┐   ┌─────────────────┐   ┌──────────────────┐
 │  agent/tools/db.py │   │agent/tools/     │   │ agent/config.py  │
 │  PostgreSQL        │   │web.py           │   │ Env var config   │
 │  (6 query tools)   │   │Brave Search API │   │                  │
 └────────────────────┘   └─────────────────┘   └──────────────────┘
```

### Module Map

```
implications-agent/
├── run.py                    # CLI entrypoint (argparse → ImplicationsAgent)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
└── agent/
    ├── __init__.py           # Package init
    ├── config.py             # Config class — loads .env vars
    ├── core.py               # ImplicationsAgent + agentic loop
    ├── prompts.py            # System prompt for the LLM
    └── tools/
        ├── __init__.py       # Re-exports all tools and registry
        ├── db.py             # 6 PostgreSQL database tools
        ├── registry.py       # Tool definitions (Anthropic format) + dispatcher
        └── web.py            # Brave Search web tool
```

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL database with the `platform_v3` schema
- Anthropic API key
- (Optional) Brave Search API key — enables the `web_search` tool

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd implications-agent

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in your credentials
```

## Usage

```bash
python run.py --news-id <NEWS_ID> --feed-id <FEED_ID> [options]
```

### CLI Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--news-id` | int | **required** | ID of the triggering news article |
| `--feed-id` | int | **required** | Feed ID (client identifier) |
| `--model` | str | from `.env` | Anthropic model override |
| `--max-turns` | int | `15` | Max agent turns before aborting |
| `--verbose` | flag | off | Print each tool call and response preview |

### Examples

```bash
# Basic usage
python run.py --news-id 12345 --feed-id 67

# Verbose mode — shows each tool call as it happens
python run.py --news-id 12345 --feed-id 67 --verbose

# Use a specific model
python run.py --news-id 12345 --feed-id 67 --model claude-opus-4-20250514

# Limit to 5 turns (faster, less thorough)
python run.py --news-id 12345 --feed-id 67 --max-turns 5
```

### Output

```
🔍 Generating implications for news_id=12345, feed_id=67...

============================================================
IMPLICATIONS
============================================================
### Strategic Impact
...

### Key Implications
- ...

### Competitive Landscape
...

### Recommended Actions
- ...

### Context & Evidence
...
```

## Configuration Reference

All settings are loaded from `.env` (or environment variables). Copy `.env.example` to `.env` to get started.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Default Claude model |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | No | `platform_v3` | Database name |
| `DB_USER` | **Yes** | — | Database username |
| `DB_PASSWORD` | **Yes** | — | Database password |
| `BRAVE_API_KEY` | No | — | Brave Search API key (web search disabled if unset) |

> **Note:** If `BRAVE_API_KEY` is not set, the `web_search` tool returns an informative error and the agent continues with database-only context.

## Tools

The agent has 7 tools registered in `agent/tools/registry.py`. Six query the PostgreSQL database; one performs live web search.

### Database Tools (`agent/tools/db.py`)

| Tool | Parameters | Description |
|---|---|---|
| `get_news` | `news_id` | Fetch full news article by ID — title, body, summary, URL, publish date |
| `search_news` | `query`, `limit=10` | Full-text search across all news via PostgreSQL `websearch_to_tsquery` |
| `search_news_for_feed` | `query`, `feed_id`, `limit=10` | Full-text search scoped to news linked to a specific client feed |
| `get_newsfeed_context` | `news_id`, `feed_id` | Newsfeed metadata — company, product, indication, matched keywords, priority |
| `get_alert_email` | `news_id`, `feed_id` | The pre-generated alert email for this news+feed pair |
| `get_recent_alerts` | `feed_id`, `limit=10` | Recent alert emails sent to a feed — useful for detecting patterns |

### Web Tool (`agent/tools/web.py`)

| Tool | Parameters | Description |
|---|---|---|
| `web_search` | `query`, `count=5` | Brave Search API — returns title, URL, and snippet for each result |

## How the Agent Loop Works

The core loop in `ImplicationsAgent.run()` (`agent/core.py`) implements the standard Anthropic tool-use pattern:

```
User message (news_id + feed_id)
         │
         ▼
  ┌──────────────────┐
  │  Claude API call  │ ◄──────────────────────────────┐
  └────────┬─────────┘                                 │
           │                                           │
    ┌──────┴───────┐                                   │
    │ tool_use     │                                   │
    │ blocks only? │                                   │
    └──────┬───────┘                                   │
           │                                           │
      Yes  ▼              No ▼                         │
   Execute each tool   Return final text               │
   via execute_tool()  ← DONE                         │
           │                                           │
           │  Append tool results as user message      │
           └───────────────────────────────────────────┘
```

1. The agent is seeded with a user message containing `news_id` and `feed_id`.
2. Claude receives the system prompt and the message history, then decides which tools to call.
3. Each tool call is dispatched through `execute_tool()` in `agent/tools/registry.py`, which wraps each tool function and serializes its output to JSON.
4. Tool results are appended to the message history as a `user`-role message (per the Anthropic tool-use protocol).
5. Steps 2–4 repeat until Claude produces a response with **only text blocks** (no `tool_use` blocks) — this is the final implications output.
6. If `max_turns` is exhausted without a text-only response, an error string is returned instead.

The agent prompt (`agent/prompts.py`) steers Claude through a specific research workflow: orient with `get_news` and `get_alert_email`, gather client context with `get_newsfeed_context`, detect patterns with `search_news_for_feed` and `get_recent_alerts`, then optionally call `web_search` before generating the structured output.
