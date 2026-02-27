# Implications Agent

Standalone agentic system that generates strategic implications for CI alerts in the pharmaceutical sector. 

Given a `news_id` + `feed_id` (client), the agent autonomously:
1. Reads the triggering news and the alert already generated
2. Analyzes the client's newsfeed context (company, product, indication, keywords)
3. Searches for related news patterns via full-text search
4. Reviews previous alerts sent to this client
5. Web searches for additional company/pipeline context if needed
6. Generates a structured implications analysis in markdown

## Architecture

```
┌──────────────────────────────────────────┐
│           Agentic Loop (core.py)         │
│                                          │
│   LLM decides → tool call → execute     │
│   ↓ repeat until implications generated  │
│                                          │
│   Tools:                                 │
│   ├─ get_news          (PostgreSQL)      │
│   ├─ get_alert_email   (PostgreSQL)      │
│   ├─ get_newsfeed_context (PostgreSQL)   │
│   ├─ search_news       (PostgreSQL FTS)  │
│   ├─ search_news_for_feed (PostgreSQL)   │
│   ├─ get_recent_alerts (PostgreSQL)      │
│   └─ web_search        (Brave API)       │
└──────────────────────────────────────────┘
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in DB credentials and API keys in .env
```

## Usage

```bash
# Basic
python run.py --news-id 12345 --feed-id 67

# With verbose tool tracing
python run.py --news-id 12345 --feed-id 67 --verbose

# Custom model
python run.py --news-id 12345 --feed-id 67 --model claude-sonnet-4-20250514
```

## Project Structure

```
implications-agent/
├── agent/
│   ├── core.py           # Agentic loop
│   ├── config.py         # Configuration (env vars)
│   ├── prompts.py        # System prompt
│   └── tools/
│       ├── db.py         # PostgreSQL tools
│       ├── web.py        # Brave web search
│       └── registry.py   # Tool definitions + dispatch
├── run.py                # CLI entrypoint
├── requirements.txt
└── .env.example
```
