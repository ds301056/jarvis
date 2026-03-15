"""Skill to type text or press key combinations."""

from skills.base import Skill
from skills.applescript_helpers import type_text, press_key


class UIType(Skill):
    name = "ui_type"
    description = (
        "Type text into the currently focused field, or press a key "
        "combination (like Return, Tab, Command+A). Use this after "
        "clicking a text field with ui_click."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to type into the focused field.",
            },
            "key": {
                "type": "string",
                "description": "Special key to press: 'return', 'tab', 'escape', 'space', 'delete', 'up', 'down', 'left', 'right', or a single letter/number.",
            },
            "modifiers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Modifier keys: 'command', 'shift', 'option', 'control'.",
            },
        },
    }

    def execute(self, text: str | None = None, key: str | None = None,
                modifiers: list[str] | None = None) -> str:
        if text:
            return type_text(text)
        if key:
            return press_key(key, modifiers)
        return "Error: provide either 'text' to type or 'key' to press."
