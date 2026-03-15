"""Skill to search and interact with the Mac App Store."""

import subprocess
import urllib.parse

from skills.base import Skill


class AppStore(Skill):
    name = "app_store"
    description = (
        "Search the Mac App Store for apps or open it to a search. "
        "Can also install apps if the 'mas' CLI tool is available."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "install"],
                "description": "'search' to find apps, 'install' to install by name.",
            },
            "query": {
                "type": "string",
                "description": "App name or search query.",
            },
        },
        "required": ["action", "query"],
    }

    def execute(self, action: str, query: str) -> str:
        if action == "search":
            return self._search(query)
        elif action == "install":
            return self._install(query)
        return f"Unknown action '{action}'."

    def _search(self, query: str) -> str:
        """Search the App Store. Uses mas CLI if available, otherwise URL scheme."""
        # Try mas CLI first (more useful — returns results)
        try:
            result = subprocess.run(
                ["mas", "search", query],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")[:10]  # Top 10
                return f"App Store results for '{query}':\n" + "\n".join(lines)
        except FileNotFoundError:
            pass  # mas not installed, fall through

        # Fallback: open App Store with search URL
        encoded = urllib.parse.quote_plus(query)
        subprocess.run(
            ["open", f"macappstore://search?term={encoded}"],
            capture_output=True, timeout=5,
        )
        return f"Opened App Store search for '{query}'."

    def _install(self, query: str) -> str:
        """Install an app using mas CLI."""
        try:
            # First search to get the app ID
            result = subprocess.run(
                ["mas", "search", query],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return f"No apps found for '{query}'. Try a different search term."

            # Parse first result — format is "ID  App Name (version)"
            first_line = result.stdout.strip().split("\n")[0]
            app_id = first_line.strip().split()[0]
            app_name = " ".join(first_line.strip().split()[1:])

            # Install
            install_result = subprocess.run(
                ["mas", "install", app_id],
                capture_output=True, text=True, timeout=120,
            )
            if install_result.returncode == 0:
                return f"Installed {app_name}."
            return f"Failed to install {app_name}: {install_result.stderr.strip()}"

        except FileNotFoundError:
            return ("The 'mas' CLI tool is not installed. Install it with: "
                    "brew install mas. For now, I've opened the App Store search instead.")
