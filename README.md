# Implications Agent

A standalone agentic system that generates strategic implications for Competitive Intelligence alerts in the pharmaceutical sector.

## Overview

When a CI alert is triggered for a client, this agent takes over to produce an **Implications** section — a strategic analysis of what the news means specifically for that company. It autonomously gathers context from the database and the web, then generates a markdown report.

```
Existing CI Alert Flow:
  news → initial_analysis → key_intelligence → ci_alerts_node → [dedup] → send

With Implications:
  news → initial_analysis → key_intelligence → ci_alerts_node →
  ┌─────────────────────────────────────────────┐
  │          IMPLICATIONS AGENT (this project)   │
  │                                              │
  │  Input: news_id + feed_id                    │
  │                                              │
  │  Agentic Loop:                               │
  │  ┌─────────────────────────────────────┐     │
  │  │ LLM decides what context it needs   │     │
  │  │         ↓                           │     │
  │  │ Calls tools (DB queries, web search)│     │
  │  │         ↓                           │     │
  │  │ Receives results, decides next step │     │
  │  │         ↓                           │     │
  │  │ Repeats until enough context        │     │
  │  │         ↓                           │     │
  │  │ Generates implications markdown     │     │
  │  └─────────────────────────────────────┘     │
  │                                              │
  │  Output: Markdown implications section       │
  └─────────────────────────────────────────────┘
  → [dedup] → send
```

## How the Agentic Loop Works

The architecture is inspired by Claude Code and OpenClaw — a tool-calling LLM loop:

1. The agent sends the task (`news_id` + `feed_id`) to the LLM with available tools
2. The LLM decides which tool(s) to call based on what context it needs
3. Tools execute (DB queries, web searches) and return results
4. Results are fed back to the LLM
5. The LLM either calls more tools or generates the final output
6. Loop continues until the LLM produces text (the implications) or hits max turns

The LLM is the decision-maker — it decides the order of tool calls, what to search for, and when it has enough context. This means the agent adapts to each alert: some may need extensive research, others may have enough context in the DB.

## Available Tools

| Tool | Source | Description |
|------|--------|-------------|
| `get_news` | PostgreSQL | Get full news article content by ID |
| `search_news` | PostgreSQL (FTS) | Full-text search across all news articles |
| `search_news_for_feed` | PostgreSQL (FTS) | Search news linked to a specific client feed |
| `get_newsfeed_context` | PostgreSQL | Get newsfeed metadata: company, product, indication, keywords, priority |
| `get_alert_email` | PostgreSQL | Get the alert email already generated for this news+feed |
| `get_recent_alerts` | PostgreSQL | Get recent alerts sent to this client with news context |
| `web_search` | Brave API | Search the web for company pipelines, regulatory actions, etc. |

## Setup

### Prerequisites

- Python 3.10+
- PostgreSQL access (Platform v3 database)
- Anthropic API key
- Brave Search API key (optional, for web search)

### Install

```bash
git clone git@github.com:lpatrocinio-avizum/implications-agent.git
cd implications-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Database (Platform v3 PostgreSQL)
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=platform_v3
DB_USER=your-user
DB_PASSWORD=your-password

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Web Search (optional)
BRAVE_API_KEY=your-brave-key
```

**Note:** The database is behind an AWS VPN. You must be connected to the VPN or have a tunnel configured.

## Usage

### Basic

```bash
python run.py --news-id 12345 --feed-id 67
```

### Verbose (trace tool calls)

```bash
python run.py --news-id 12345 --feed-id 67 --verbose
```

Verbose output shows each tool call and response:
```
🔍 Generating implications for news_id=12345, feed_id=67...

--- Turn 1 ---
  🔧 get_news({"news_id": 12345})
  ← {"news_id": 12345, "title": "FDA Approves...", ...}
  🔧 get_newsfeed_context({"news_id": 12345, "feed_id": 67})
  ← {"company": "Novartis", "product": "Kisqali", ...}

--- Turn 2 ---
  🔧 get_recent_alerts({"feed_id": 67, "limit": 5})
  ← [{"alert_title": "...", ...}]

--- Turn 3 ---
  🔧 web_search({"query": "Novartis Kisqali pipeline 2026"})
  ← [{"title": "...", "url": "..."}]

✅ Agent finished after 4 turns

============================================================
IMPLICATIONS
============================================================
### Strategic Impact
...
```

### Custom model

```bash
python run.py --news-id 12345 --feed-id 67 --model claude-sonnet-4-20250514
```

### Max turns

```bash
python run.py --news-id 12345 --feed-id 67 --max-turns 20
```

## Configuration Reference

| Env Variable | Required | Default | Description |
|-------------|----------|---------|-------------|
| `DB_HOST` | Yes | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `DB_NAME` | Yes | `platform_v3` | Database name |
| `DB_USER` | Yes | — | Database user |
| `DB_PASSWORD` | Yes | — | Database password |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-20250514` | Model to use |
| `BRAVE_API_KEY` | No | — | Brave Search API key (web search disabled without it) |

## Database Schema

The agent reads from three tables in the `public` schema:

- **`news`** — News article content. Has `search_content` tsvector for full-text search.
- **`news_feed`** — Junction table linking news to client feeds. Contains metadata: `company`, `product`, `indication`, `match` (keywords), `summary`, `news_priority_id` (6 = alert).
- **`news_alert_emails`** — Alert emails already generated. Contains `alert_title` and `body`.

## Project Structure

```
implications-agent/
├── agent/
│   ├── __init__.py
│   ├── core.py           # Agentic loop — LLM tool-calling loop
│   ├── config.py         # Configuration from environment variables
│   ├── prompts.py        # System prompt (pharma CI analyst persona)
│   └── tools/
│       ├── __init__.py
│       ├── db.py         # 6 PostgreSQL tools
│       ├── web.py        # Brave web search tool
│       └── registry.py   # Tool definitions (Anthropic format) + dispatch
├── run.py                # CLI entrypoint
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Output Format

The agent produces markdown with these sections:

- **Strategic Impact** — 2-3 sentence executive summary
- **Key Implications** — 3-5 specific, actionable bullet points tied to the client's context
- **Competitive Landscape** — How the news shifts competitive dynamics
- **Recommended Actions** — 2-3 concrete next steps
- **Context & Evidence** — Sources that informed the analysis
