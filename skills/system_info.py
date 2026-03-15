"""Skill to get system information: time, date, uptime, memory."""

import subprocess
from datetime import datetime

from skills.base import Skill


class SystemInfo(Skill):
    name = "system_info"
    description = "Get current time, date, system uptime, or memory usage on macOS."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "enum": ["time", "date", "datetime", "uptime", "memory"],
                "description": "What system info to retrieve.",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str) -> str:
        now = datetime.now()

        if query == "time":
            return f"The current time is {now.strftime('%I:%M %p')}."
        elif query == "date":
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        elif query == "datetime":
            return f"It's {now.strftime('%A, %B %d, %Y at %I:%M %p')}."
        elif query == "uptime":
            result = subprocess.run(
                ["uptime"], capture_output=True, text=True, timeout=5,
            )
            return f"System uptime: {result.stdout.strip()}"
        elif query == "memory":
            # Get memory pressure summary
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5,
            )
            # Parse page size and free pages for a simple summary
            lines = result.stdout.strip().split("\n")
            return f"Memory stats:\n{chr(10).join(lines[:6])}"
        else:
            return f"Unknown query '{query}'. Use: time, date, datetime, uptime, memory."
