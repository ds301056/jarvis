"""Skill to open/launch macOS applications."""

import subprocess

from skills.base import Skill


class OpenApp(Skill):
    name = "open_app"
    description = "Launch or switch to a macOS application by name."
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "The application name, e.g. 'Safari', 'Terminal', 'Finder'",
            },
        },
        "required": ["app_name"],
    }

    def execute(self, app_name: str) -> str:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return f"Opened {app_name}."
        return f"Failed to open {app_name}: {result.stderr.strip()}"
