"""Skill to read/write the macOS clipboard."""

import subprocess

from skills.base import Skill


class Clipboard(Skill):
    name = "clipboard"
    description = "Read from or write to the macOS clipboard (pasteboard)."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "'read' to get clipboard contents, 'write' to set them.",
            },
            "text": {
                "type": "string",
                "description": "Text to write to clipboard (only used with action='write').",
            },
        },
        "required": ["action"],
    }

    def execute(self, action: str, text: str | None = None) -> str:
        if action == "read":
            result = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=5,
            )
            content = result.stdout
            if not content:
                return "Clipboard is empty."
            # Truncate very long clipboard contents
            if len(content) > 500:
                return f"Clipboard contents (truncated): {content[:500]}..."
            return f"Clipboard contents: {content}"

        elif action == "write":
            if not text:
                return "Error: no text provided to write to clipboard."
            subprocess.run(
                ["pbcopy"], input=text, text=True, timeout=5,
            )
            return f"Copied to clipboard: {text[:100]}{'...' if len(text) > 100 else ''}"

        return f"Unknown action '{action}'. Use 'read' or 'write'."
