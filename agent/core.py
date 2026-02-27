"""Core agentic loop for the Implications Agent.

Inspired by Claude Code / OpenClaw architecture:
- LLM decides which tools to call
- Tools execute and return results
- Loop continues until LLM produces final text output
"""

import json
import anthropic
from agent.config import Config
from agent.prompts import SYSTEM_PROMPT
from agent.tools.registry import TOOLS, execute_tool


class ImplicationsAgent:
    def __init__(self, model: str | None = None, max_turns: int = 15, verbose: bool = False):
        """Initialise the agent.

        Args:
            model: Anthropic model ID to use.  Defaults to ``Config.MODEL``
                (``ANTHROPIC_MODEL`` env var, or ``claude-sonnet-4-20250514``).
            max_turns: Maximum number of tool-use / response round-trips before
                the loop is aborted and an error string is returned.
            verbose: When ``True``, print each tool call name + arguments and
                a short preview of the result to stdout.
        """
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL
        self.max_turns = max_turns
        self.verbose = verbose

    def run(self, news_id: int, feed_id: int) -> str:
        """Run the agent loop and return the implications markdown."""
        messages = [
            {
                "role": "user",
                "content": (
                    f"Generate the Implications section for this alert.\n\n"
                    f"- news_id: {news_id}\n"
                    f"- feed_id: {feed_id}\n\n"
                    f"Use your tools to gather all necessary context before generating."
                ),
            }
        ]

        for turn in range(self.max_turns):
            if self.verbose:
                print(f"\n--- Turn {turn + 1} ---")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Check if we have tool calls
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            text_blocks = [block for block in response.content if block.type == "text"]

            if not tool_calls:
                # No more tool calls — LLM is done, extract final text
                result = "\n".join(block.text for block in text_blocks)
                if self.verbose:
                    print(f"\n✅ Agent finished after {turn + 1} turns")
                return result

            # Append assistant message with tool calls
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and build tool results
            tool_results = []
            for tc in tool_calls:
                if self.verbose:
                    print(f"  🔧 {tc.name}({json.dumps(tc.input, ensure_ascii=False)})")

                result = execute_tool(tc.name, tc.input)

                if self.verbose:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"  ← {preview}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        # Max turns reached
        if self.verbose:
            print(f"\n⚠️ Max turns ({self.max_turns}) reached")
        return "Error: Agent exceeded maximum turns without producing a result."
