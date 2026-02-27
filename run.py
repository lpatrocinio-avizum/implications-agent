#!/usr/bin/env python3
"""CLI entrypoint for the Implications Agent.

Usage:
    python run.py --news-id 12345 --feed-id 67
    python run.py --news-id 12345 --feed-id 67 --verbose
    python run.py --news-id 12345 --feed-id 67 --model claude-sonnet-4-20250514
"""

import argparse
import sys
from agent.core import ImplicationsAgent


def main():
    """Parse CLI arguments and run the Implications Agent.

    Reads ``--news-id`` and ``--feed-id`` from the command line, constructs
    an :class:`~agent.core.ImplicationsAgent`, runs the agentic loop, and
    prints the resulting implications markdown to stdout.
    """
    parser = argparse.ArgumentParser(description="Generate alert implications")
    parser.add_argument("--news-id", type=int, required=True, help="News article ID")
    parser.add_argument("--feed-id", type=int, required=True, help="Feed ID (client)")
    parser.add_argument("--model", type=str, default=None, help="Anthropic model to use")
    parser.add_argument("--max-turns", type=int, default=15, help="Max agent turns")
    parser.add_argument("--verbose", action="store_true", help="Print tool calls and responses")
    args = parser.parse_args()

    agent = ImplicationsAgent(
        model=args.model,
        max_turns=args.max_turns,
        verbose=args.verbose,
    )

    print(f"🔍 Generating implications for news_id={args.news_id}, feed_id={args.feed_id}...\n")

    result = agent.run(news_id=args.news_id, feed_id=args.feed_id)

    print("\n" + "=" * 60)
    print("IMPLICATIONS")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
