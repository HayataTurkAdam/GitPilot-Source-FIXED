import json
from pathlib import Path

APP_DIR = Path.home() / "AppData" / "Roaming" / "GitPilot"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULTS = {"accounts": [], "repositories": [], "theme": "dark"}

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULTS)
        return DEFAULTS.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, json.JSONDecodeError):
        return DEFAULTS.copy()

def save_config(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
