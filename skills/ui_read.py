"""Skill to read UI elements from the frontmost app window."""

from skills.base import Skill
from skills.applescript_helpers import get_ui_elements, get_frontmost_app


class UIRead(Skill):
    name = "ui_read"
    description = (
        "Read the UI elements visible in the frontmost app window. "
        "Returns element names and types (buttons, text fields, labels, etc.) "
        "so you know what can be clicked or interacted with. "
        "Always use this before trying to click or interact with UI elements."
    )
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "App to read from. Omit to use the frontmost app.",
            },
        },
    }

    def execute(self, app_name: str | None = None) -> str:
        if not app_name:
            app_name = get_frontmost_app()
        elements = get_ui_elements(app_name)
        return f"UI elements in {app_name}:\n{elements}"
