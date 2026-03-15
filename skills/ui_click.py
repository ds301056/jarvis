"""Skill to click UI elements by name."""

from skills.base import Skill
from skills.applescript_helpers import click_element_by_name, get_frontmost_app


class UIClick(Skill):
    name = "ui_click"
    description = (
        "Click a button, menu item, or other UI element by its name "
        "in the frontmost app. Use ui_read first to see available elements."
    )
    parameters = {
        "type": "object",
        "properties": {
            "element_name": {
                "type": "string",
                "description": "The name of the element to click, e.g. 'General', 'Save', 'OK'.",
            },
            "element_type": {
                "type": "string",
                "description": "Type of element: 'button', 'menu item', 'checkbox', 'static text', 'row'. Default: 'button'.",
            },
            "app_name": {
                "type": "string",
                "description": "App to click in. Omit to use the frontmost app.",
            },
        },
        "required": ["element_name"],
    }

    def execute(self, element_name: str, element_type: str = "button",
                app_name: str | None = None) -> str:
        return click_element_by_name(element_name, element_type, app_name)
