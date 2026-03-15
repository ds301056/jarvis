"""Skill to search contacts and initiate calls."""

import subprocess

from skills.base import Skill
from skills.applescript_helpers import run_applescript


class Contacts(Skill):
    name = "contacts"
    description = (
        "Search contacts by name to get their phone number or email, "
        "or initiate a phone call or FaceTime call."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "call", "facetime"],
                "description": "Action: 'search' to find contact info, 'call' to phone, 'facetime' for video call.",
            },
            "name": {
                "type": "string",
                "description": "Contact name to search for.",
            },
        },
        "required": ["action", "name"],
    }

    def execute(self, action: str, name: str) -> str:
        if action == "search":
            return self._search(name)
        elif action == "call":
            return self._initiate(name, "tel")
        elif action == "facetime":
            return self._initiate(name, "facetime")
        return f"Unknown action '{action}'."

    def _search(self, name: str) -> str:
        """Search for a contact and return their info."""
        script = f'''
tell application "Contacts"
    set matchedPeople to every person whose name contains "{name}"
    if (count of matchedPeople) is 0 then
        return "No contacts found matching '{name}'."
    end if

    set output to ""
    repeat with p in matchedPeople
        set output to output & "Name: " & (name of p) & linefeed
        try
            repeat with ph in phones of p
                set output to output & "  Phone: " & (value of ph) & " (" & (label of ph) & ")" & linefeed
            end repeat
        end try
        try
            repeat with em in emails of p
                set output to output & "  Email: " & (value of em) & " (" & (label of em) & ")" & linefeed
            end repeat
        end try
        set output to output & linefeed
    end repeat
    return output
end tell
'''
        try:
            result = run_applescript(script)
            return result if result else f"No contacts found matching '{name}'."
        except Exception as e:
            return f"Error searching contacts: {e}"

    def _initiate(self, name: str, scheme: str) -> str:
        """Find a contact's phone number and initiate a call."""
        # First find the phone number
        script = f'''
tell application "Contacts"
    set matchedPeople to every person whose name contains "{name}"
    if (count of matchedPeople) is 0 then
        return "NOT_FOUND"
    end if
    set p to item 1 of matchedPeople
    try
        set phoneNum to value of item 1 of phones of p
        return phoneNum
    end try
    return "NO_PHONE"
end tell
'''
        try:
            result = run_applescript(script)
            if result == "NOT_FOUND":
                return f"No contact found matching '{name}'."
            if result == "NO_PHONE":
                return f"Contact '{name}' has no phone number."

            phone = result.strip()
            # Clean phone number for URL
            clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
            subprocess.run(["open", f"{scheme}:{clean_phone}"], timeout=5)

            action_name = "Calling" if scheme == "tel" else "FaceTiming"
            return f"{action_name} {name} at {phone}."
        except Exception as e:
            return f"Error initiating call: {e}"
