"""Skill to open URLs or search the web."""

import subprocess
import urllib.parse

from skills.base import Skill


class WebSearch(Skill):
    name = "web_search"
    description = "Open a URL in the default browser or search Google for a query."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A search query or a full URL to open.",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str) -> str:
        # If it looks like a URL, open it directly
        if query.startswith(("http://", "https://", "www.")):
            url = query if query.startswith("http") else f"https://{query}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"

        subprocess.run(["open", url], capture_output=True, timeout=5)
        if query.startswith(("http://", "https://", "www.")):
            return f"Opened {url} in the browser."
        return f"Searching Google for '{query}'."
