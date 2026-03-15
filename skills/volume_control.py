"""Skill to control macOS system volume."""

import subprocess

from skills.base import Skill


class VolumeControl(Skill):
    name = "volume_control"
    description = "Set the system volume level (0-100) or mute/unmute on macOS."
    parameters = {
        "type": "object",
        "properties": {
            "level": {
                "type": "integer",
                "description": "Volume level from 0 to 100. Omit to just mute/unmute.",
            },
            "mute": {
                "type": "boolean",
                "description": "True to mute, False to unmute. Omit to leave mute state unchanged.",
            },
        },
    }

    def execute(self, level: int | None = None, mute: bool | None = None) -> str:
        results = []

        if mute is not None:
            mute_str = "true" if mute else "false"
            subprocess.run(
                ["osascript", "-e", f"set volume output muted {mute_str}"],
                capture_output=True, timeout=5,
            )
            results.append("Muted." if mute else "Unmuted.")

        if level is not None:
            # macOS volume is 0-7 scale internally; osascript output volume is 0-100
            clamped = max(0, min(100, level))
            subprocess.run(
                ["osascript", "-e", f"set volume output volume {clamped}"],
                capture_output=True, timeout=5,
            )
            results.append(f"Volume set to {clamped}%.")

        return " ".join(results) if results else "No volume changes made. Specify level or mute."
