"""Skill to control Apple Music playback."""

import subprocess

from skills.base import Skill


def _osascript(script: str) -> str:
    """Run an AppleScript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip()


class MusicControl(Skill):
    name = "music_control"
    description = "Control Apple Music: play, pause, next/previous track, or get now playing info."
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["play", "pause", "toggle", "next", "previous", "now_playing"],
                "description": "The playback action to perform.",
            },
        },
        "required": ["action"],
    }

    def execute(self, action: str) -> str:
        app = "Music"

        if action == "play":
            _osascript(f'tell application "{app}" to play')
            return "Music is now playing."
        elif action == "pause":
            _osascript(f'tell application "{app}" to pause')
            return "Music paused."
        elif action == "toggle":
            _osascript(f'tell application "{app}" to playpause')
            return "Toggled music playback."
        elif action == "next":
            _osascript(f'tell application "{app}" to next track')
            return "Skipped to next track."
        elif action == "previous":
            _osascript(f'tell application "{app}" to previous track')
            return "Went to previous track."
        elif action == "now_playing":
            try:
                name = _osascript(f'tell application "{app}" to get name of current track')
                artist = _osascript(f'tell application "{app}" to get artist of current track')
                if name:
                    return f"Now playing: {name} by {artist}"
                return "No track is currently playing."
            except Exception:
                return "Could not get now playing info. Music may not be running."

        return f"Unknown action '{action}'."
