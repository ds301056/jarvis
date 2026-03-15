"""Shared AppleScript utilities for UI automation skills."""

import subprocess


def run_applescript(script: str, timeout: int = 10) -> str:
    """Run an AppleScript and return stdout. Raises on timeout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0 and result.stderr.strip():
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def get_frontmost_app() -> str:
    """Return the name of the frontmost application."""
    return run_applescript(
        'tell application "System Events" to get name of first application process '
        'whose frontmost is true'
    )


def get_ui_elements(app_name: str | None = None, max_depth: int = 2) -> str:
    """Return the accessibility tree of the frontmost window as text.

    Uses System Events to enumerate UI elements. Output is truncated
    to ~2000 chars to keep LLM context manageable.
    """
    if not app_name:
        app_name = get_frontmost_app()

    # AppleScript to recursively list UI elements with indentation
    script = f'''
tell application "System Events"
    tell process "{app_name}"
        set frontWindow to window 1
        set output to ""
        set output to output & my listElements(frontWindow, 0, {max_depth})
        return output
    end tell
end tell

on listElements(theElement, depth, maxDepth)
    if depth > maxDepth then return ""
    set indent to ""
    repeat depth times
        set indent to indent & "  "
    end repeat

    set elementRole to role of theElement
    set elementName to ""
    try
        set elementName to name of theElement
    end try
    set elementValue to ""
    try
        set elementValue to value of theElement
        if elementValue is not "" and elementValue is not missing value then
            set elementValue to " [" & (elementValue as text) & "]"
        else
            set elementValue to ""
        end if
    end try

    set output to ""
    if elementName is not "" then
        set output to indent & elementRole & " \\"" & elementName & "\\"" & elementValue & linefeed
    else if elementRole is not "AXGroup" and elementRole is not "AXUnknown" then
        set output to indent & elementRole & elementValue & linefeed
    end if

    try
        set childElements to UI elements of theElement
        repeat with child in childElements
            set output to output & my listElements(child, depth + 1, maxDepth)
        end repeat
    end try

    return output
end listElements
'''
    try:
        result = run_applescript(script, timeout=10)
    except subprocess.TimeoutExpired:
        return f"Error: reading UI elements from {app_name} timed out (UI may be too complex)."
    except RuntimeError as e:
        return f"Error reading UI elements: {e}"

    # Truncate to keep LLM context reasonable
    if len(result) > 2000:
        result = result[:2000] + "\n... (truncated)"

    return result if result else f"No UI elements found in {app_name}'s frontmost window."


def click_element_by_name(element_name: str, element_type: str = "button",
                          app_name: str | None = None) -> str:
    """Click a UI element by name using System Events."""
    if not app_name:
        app_name = get_frontmost_app()

    script = f'''
tell application "System Events"
    tell process "{app_name}"
        click {element_type} "{element_name}" of window 1
    end tell
end tell
'''
    try:
        run_applescript(script)
        return f"Clicked {element_type} '{element_name}' in {app_name}."
    except RuntimeError:
        # Try searching deeper — element might be in a group/scroll area
        script_deep = f'''
tell application "System Events"
    tell process "{app_name}"
        click (first {element_type} whose name is "{element_name}") of window 1
    end tell
end tell
'''
        try:
            run_applescript(script_deep)
            return f"Clicked {element_type} '{element_name}' in {app_name}."
        except RuntimeError as e:
            return f"Could not click {element_type} '{element_name}' in {app_name}: {e}"


def type_text(text: str) -> str:
    """Type text using System Events keystroke."""
    # Escape backslashes and quotes for AppleScript
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{escaped}"'
    try:
        run_applescript(script)
        return f"Typed: {text}"
    except RuntimeError as e:
        return f"Error typing text: {e}"


def press_key(key: str, modifiers: list[str] | None = None) -> str:
    """Press a key combination using System Events.

    key: 'return', 'tab', 'escape', 'space', 'delete', or a letter/number
    modifiers: list of 'command', 'shift', 'option', 'control'
    """
    # Map common key names to AppleScript key codes
    key_code_map = {
        "return": 36, "enter": 36,
        "tab": 48,
        "escape": 53, "esc": 53,
        "space": 49,
        "delete": 51, "backspace": 51,
        "up": 126, "down": 125, "left": 123, "right": 124,
    }

    if modifiers:
        mod_str = ", ".join(f"{m} down" for m in modifiers)
        using_clause = f" using {{{mod_str}}}"
    else:
        using_clause = ""

    key_lower = key.lower()
    if key_lower in key_code_map:
        script = f'tell application "System Events" to key code {key_code_map[key_lower]}{using_clause}'
    elif len(key) == 1:
        script = f'tell application "System Events" to keystroke "{key}"{using_clause}'
    else:
        return f"Unknown key: {key}"

    try:
        run_applescript(script)
        mod_desc = f" with {'+'.join(modifiers)}" if modifiers else ""
        return f"Pressed {key}{mod_desc}."
    except RuntimeError as e:
        return f"Error pressing key: {e}"
