"""Skill to navigate System Settings to a specific section."""

import subprocess
import time

from skills.base import Skill


# macOS Ventura+ System Settings pane IDs
_PANE_IDS = {
    "general": "com.apple.settings.General",
    "appearance": "com.apple.Appearance-Settings.extension",
    "accessibility": "com.apple.Accessibility-Settings.extension",
    "control center": "com.apple.ControlCenter-Settings.extension",
    "desktop": "com.apple.Desktop-Settings.extension",
    "dock": "com.apple.Dock-Settings.extension",
    "displays": "com.apple.Displays-Settings.extension",
    "display": "com.apple.Displays-Settings.extension",
    "wallpaper": "com.apple.Wallpaper-Settings.extension",
    "screen saver": "com.apple.ScreenSaver-Settings.extension",
    "battery": "com.apple.settings.Battery",
    "lock screen": "com.apple.Lock-Screen-Settings.extension",
    "users": "com.apple.settings.Users",
    "passwords": "com.apple.Passwords-Settings.extension",
    "internet accounts": "com.apple.Internet-Accounts-Settings.extension",
    "game center": "com.apple.Game-Center-Settings.extension",
    "wallet": "com.apple.WalletSettingsExtension",
    "keyboard": "com.apple.Keyboard-Settings.extension",
    "trackpad": "com.apple.Trackpad-Settings.extension",
    "mouse": "com.apple.Mouse-Settings.extension",
    "printers": "com.apple.Print-Scan-Settings.extension",
    "sound": "com.apple.Sound-Settings.extension",
    "notifications": "com.apple.Notifications-Settings.extension",
    "focus": "com.apple.Focus-Settings.extension",
    "screen time": "com.apple.Screen-Time-Settings.extension",
    "privacy": "com.apple.settings.PrivacySecurity.extension",
    "security": "com.apple.settings.PrivacySecurity.extension",
    "network": "com.apple.Network-Settings.extension",
    "wifi": "com.apple.wifi-settings-extension",
    "wi-fi": "com.apple.wifi-settings-extension",
    "bluetooth": "com.apple.BluetoothSettings",
    "vpn": "com.apple.NetworkExtensionSettingsUI.NESettingsUIExtension",
    "siri": "com.apple.Siri-Settings.extension",
    "spotlight": "com.apple.Siri-Settings.extension",
    "apple id": "com.apple.systempreferences.AppleIDSettings",
    "icloud": "com.apple.systempreferences.AppleIDSettings",
    "software update": "com.apple.Software-Update-Settings.extension",
    "storage": "com.apple.settings.Storage",
    "time machine": "com.apple.Time-Machine-Settings.extension",
    "startup disk": "com.apple.Startup-Disk-Settings.extension",
}


class SystemSettings(Skill):
    name = "system_settings"
    description = (
        "Open a specific section of System Settings (General, Wi-Fi, Bluetooth, "
        "Display, Sound, Notifications, Privacy, Network, Battery, etc.)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": (
                    "Settings section to open: general, wifi, bluetooth, display, "
                    "sound, notifications, battery, privacy, network, keyboard, "
                    "trackpad, mouse, accessibility, appearance, wallpaper, "
                    "dock, siri, apple id, software update, storage, etc."
                ),
            },
        },
        "required": ["section"],
    }

    def execute(self, section: str) -> str:
        section_lower = section.lower().strip()
        pane_id = _PANE_IDS.get(section_lower)

        if not pane_id:
            available = ", ".join(sorted(_PANE_IDS.keys()))
            return f"Unknown section '{section}'. Available: {available}"

        try:
            # Open System Settings to the specific pane
            subprocess.run(
                ["open", f"x-apple.systempreferences:{pane_id}"],
                capture_output=True, timeout=5,
            )
            time.sleep(0.5)  # Brief pause for the pane to load
            return f"Opened System Settings > {section.title()}."
        except Exception as e:
            return f"Error opening System Settings: {e}"
