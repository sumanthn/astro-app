"""Claude API client for Vedic analysis."""
import os
import json
import re
import anthropic
from typing import Optional


class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def analyze(self, system: str, user: str, max_tokens: int = 8000) -> str:
        """Send a prompt and return text response. Uses streaming for large requests."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            response = stream.get_final_message()
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        return response.content[0].text

    def analyze_json(self, system: str, user: str, max_tokens: int = 32000) -> dict:
        """Send a prompt and parse JSON response."""
        system_with_json = system + "\n\nYou MUST respond with valid JSON only. No markdown fences, no preamble, no text after the JSON."
        text = self.analyze(system_with_json, user, max_tokens)
        text = text.strip()

        # Remove markdown fences if present
        if text.startswith("```"):
            # Find the JSON content between fences
            match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
            else:
                lines = text.split("\n")
                text = "\n".join(lines[1:])

        # Try parsing as-is
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # If truncated, try to repair by closing open braces/brackets
            repaired = self._repair_json(text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                # Last resort: return as raw text wrapped in dict
                return {"raw_response": text, "parse_error": True}

    def _repair_json(self, text: str) -> str:
        """Attempt to repair truncated JSON by closing unclosed braces/brackets."""
        # Remove trailing incomplete string/value
        # Find last complete key-value pair
        text = text.rstrip()
        if text.endswith(","):
            text = text[:-1]

        # Count unclosed braces and brackets
        opens = 0
        open_brackets = 0
        in_string = False
        escape = False

        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                opens += 1
            elif ch == '}':
                opens -= 1
            elif ch == '[':
                open_brackets += 1
            elif ch == ']':
                open_brackets -= 1

        # If we're in a string, close it
        if in_string:
            text += '"'

        # Close brackets and braces
        text += ']' * open_brackets + '}' * opens

        return text

    def token_usage(self) -> dict:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total": self.total_input_tokens + self.total_output_tokens,
        }
