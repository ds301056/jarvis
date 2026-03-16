"""Settings persistence — read/write ~/.jarvis/settings.json and hot-patch config."""

import json
import os

import config

SETTINGS_PATH = os.path.expanduser("~/.jarvis/settings.json")

# Map settings keys to config module attribute names
_CONFIG_MAP = {
    "llm_provider": "LLM_PROVIDER",
    "ollama_model": "OLLAMA_MODEL",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "anthropic_model": "ANTHROPIC_MODEL",
    "openai_api_key": "OPENAI_API_KEY",
    "openai_model": "OPENAI_MODEL",
    "gemini_api_key": "GEMINI_API_KEY",
    "gemini_model": "GEMINI_MODEL",
    "tts_backend": "TTS_BACKEND",
    "stt_backend": "STT_BACKEND",
}


def load_settings() -> dict:
    """Load settings from disk. Returns empty dict if file doesn't exist."""
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(data: dict):
    """Save settings to disk and hot-patch the config module."""
    # Load existing, merge new values (ignore masked keys)
    current = load_settings()
    for key, value in data.items():
        if key not in _CONFIG_MAP:
            continue
        # Don't overwrite with masked values
        if isinstance(value, str) and (value.startswith("sk-...") or value == "****" or "..." in value):
            continue
        current[key] = value

    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(current, f, indent=2)

    # Hot-patch config module
    _apply_to_config(current)


def _apply_to_config(settings: dict):
    """Set config module attributes from settings dict."""
    for key, value in settings.items():
        attr = _CONFIG_MAP.get(key)
        if attr and value:
            setattr(config, attr, value)


def mask_key(key: str) -> str:
    """Mask an API key for safe display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "..." + key[-4:]


# On import, apply any saved settings so they take effect at startup
_apply_to_config(load_settings())
