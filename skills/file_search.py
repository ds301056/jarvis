"""Search for files on this Mac by content or name."""

from skills.base import Skill


class FileSearchSkill(Skill):
    name = "file_search"
    description = (
        "Search for files on this Mac by content or name. "
        "Use when the user asks to find, locate, or search for documents, files, or data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for (e.g. 'tax documents', 'python tutorial', 'meeting notes')",
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str = "", **kwargs) -> str:
        if not query:
            return "No search query provided."

        from indexer.search import search

        results = search(query, limit=5)

        if not results:
            return f"No files found matching '{query}'."

        lines = [f"Found {len(results)} result(s) for '{query}':\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['file_name']} ({r['extension']})")
            lines.append(f"   Path: {r['file_path']}")
            lines.append(f"   Snippet: {r['snippet']}")
            lines.append("")

        return "\n".join(lines)
