"""Skill to control Safari: search, navigate, read pages, fill forms."""

import json

from skills.base import Skill
from skills.applescript_helpers import run_applescript


def _safari_js(js_code: str) -> str:
    """Execute JavaScript in Safari's current tab and return the result."""
    # Escape for AppleScript string embedding
    escaped = js_code.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Safari" to do JavaScript "{escaped}" in current tab of window 1'
    return run_applescript(script, timeout=10)


class Safari(Skill):
    name = "safari"
    description = (
        "Control Safari: search the web, open URLs, read page content, "
        "get form fields, fill form fields, or click links on the current page."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "open_url", "get_page_info", "read_page",
                         "get_form_fields", "fill_field", "click_link"],
                "description": "The action to perform.",
            },
            "query": {
                "type": "string",
                "description": "Search query (for 'search' action).",
            },
            "url": {
                "type": "string",
                "description": "URL to open (for 'open_url' action).",
            },
            "field_name": {
                "type": "string",
                "description": "Form field name or id (for 'fill_field' action).",
            },
            "value": {
                "type": "string",
                "description": "Value to fill (for 'fill_field' action).",
            },
            "link_text": {
                "type": "string",
                "description": "Link text to click (for 'click_link' action).",
            },
        },
        "required": ["action"],
    }

    def execute(self, action: str, query: str | None = None, url: str | None = None,
                field_name: str | None = None, value: str | None = None,
                link_text: str | None = None) -> str:

        if action == "search":
            if not query:
                return "Error: 'query' is required for search."
            import urllib.parse
            search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
            run_applescript(f'''
tell application "Safari"
    activate
    if (count of windows) is 0 then
        make new document
    end if
    set URL of current tab of window 1 to "{search_url}"
end tell
''')
            return f"Searching Google for '{query}' in Safari."

        elif action == "open_url":
            if not url:
                return "Error: 'url' is required for open_url."
            if not url.startswith("http"):
                url = f"https://{url}"
            run_applescript(f'''
tell application "Safari"
    activate
    if (count of windows) is 0 then
        make new document
    end if
    set URL of current tab of window 1 to "{url}"
end tell
''')
            return f"Opened {url} in Safari."

        elif action == "get_page_info":
            title = run_applescript(
                'tell application "Safari" to get name of current tab of window 1'
            )
            page_url = run_applescript(
                'tell application "Safari" to get URL of current tab of window 1'
            )
            return f"Page: {title}\nURL: {page_url}"

        elif action == "read_page":
            try:
                text = _safari_js("document.body.innerText")
                if len(text) > 2000:
                    text = text[:2000] + "\n... (truncated)"
                return f"Page text:\n{text}" if text else "Page appears empty."
            except Exception as e:
                return f"Error reading page: {e}"

        elif action == "get_form_fields":
            try:
                js = """
(function() {
    var fields = [];
    var inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(function(el) {
        var label = '';
        if (el.id) {
            var labelEl = document.querySelector('label[for=\"' + el.id + '\"]');
            if (labelEl) label = labelEl.innerText;
        }
        if (!label) label = el.getAttribute('aria-label') || el.placeholder || '';
        fields.push({
            tag: el.tagName.toLowerCase(),
            type: el.type || '',
            name: el.name || '',
            id: el.id || '',
            label: label,
            value: el.value || ''
        });
    });
    return JSON.stringify(fields);
})()
"""
                result = _safari_js(js)
                fields = json.loads(result)
                if not fields:
                    return "No form fields found on this page."
                lines = []
                for f in fields[:30]:  # Limit to 30 fields
                    desc = f.get("label") or f.get("name") or f.get("id") or "(unnamed)"
                    lines.append(f"  {f['tag']}[{f['type']}] name='{f['name']}' id='{f['id']}' label='{desc}' value='{f['value']}'")
                return f"Form fields ({len(fields)} found):\n" + "\n".join(lines)
            except Exception as e:
                return f"Error reading form fields: {e}"

        elif action == "fill_field":
            if not field_name or not value:
                return "Error: 'field_name' and 'value' are required for fill_field."
            escaped_value = value.replace("'", "\\'")
            # Try by name first, then id, then placeholder
            js = f"""
(function() {{
    var el = document.querySelector('input[name=\\"{field_name}\\"], textarea[name=\\"{field_name}\\"]')
        || document.getElementById('{field_name}')
        || document.querySelector('input[placeholder*=\\"{field_name}\\"], textarea[placeholder*=\\"{field_name}\\"]');
    if (!el) return 'Field not found: {field_name}';
    el.value = '{escaped_value}';
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
    return 'Filled ' + (el.name || el.id || '{field_name}') + ' with value.';
}})()
"""
            try:
                result = _safari_js(js)
                return result
            except Exception as e:
                return f"Error filling field: {e}"

        elif action == "click_link":
            if not link_text:
                return "Error: 'link_text' is required for click_link."
            js = f"""
(function() {{
    var links = document.querySelectorAll('a');
    for (var i = 0; i < links.length; i++) {{
        if (links[i].innerText.trim().toLowerCase().includes('{link_text.lower()}')) {{
            links[i].click();
            return 'Clicked link: ' + links[i].innerText.trim();
        }}
    }}
    return 'No link found containing: {link_text}';
}})()
"""
            try:
                result = _safari_js(js)
                return result
            except Exception as e:
                return f"Error clicking link: {e}"

        return f"Unknown action '{action}'."
