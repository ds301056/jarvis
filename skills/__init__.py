"""Skills registry with auto-discovery.

On import, scans this package for all Skill subclasses and builds a registry.
"""

import importlib
import pathlib
import traceback

from skills.base import Skill

_SKILL_MAP: dict[str, Skill] = {}


def _discover_skills():
    """Find and instantiate all Skill subclasses in this package."""
    pkg_dir = pathlib.Path(__file__).parent
    for py_file in pkg_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "base.py":
            continue
        module_name = f"skills.{py_file.stem}"
        try:
            module = importlib.import_module(module_name)
        except Exception:
            traceback.print_exc()
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, Skill)
                    and attr is not Skill
                    and attr.name):
                _SKILL_MAP[attr.name] = attr()


def get_ollama_tools() -> list[dict]:
    """Return tool definitions in Ollama's /api/chat format."""
    tools = []
    for skill in _SKILL_MAP.values():
        tools.append({
            "type": "function",
            "function": {
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.parameters,
            },
        })
    return tools


def execute_tool(name: str, args: dict) -> str:
    """Execute a skill by name. Returns result string or error message."""
    skill = _SKILL_MAP.get(name)
    if skill is None:
        return f"Error: unknown tool '{name}'. Available tools: {', '.join(_SKILL_MAP.keys())}"
    try:
        return skill.execute(**args)
    except Exception as e:
        return f"Error executing {name}: {e}"


# Auto-discover on import
_discover_skills()
