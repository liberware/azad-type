"""Small, validated settings store. Typing content is never persisted."""
import json
import os
from pathlib import Path
import tempfile


def data_directory():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "AzadType"


def load_settings(path):
    path = Path(path)
    if not path.exists():
        return {}
    if path.stat().st_size > 65536:
        raise ValueError("Settings file is too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Settings must be a JSON object")
    allowed = value.get("allowed_apps", [])
    if not isinstance(allowed, list) or any(not isinstance(a, str) or not a.lower().endswith(".exe")
                                            or any(c in a for c in '/\\\r\n') for a in allowed):
        raise ValueError("Allowed applications must be executable basenames")
    result = {"allowed_apps": sorted(set(a.lower() for a in allowed))}
    for key in ("persian_digits", "persian_punctuation"):
        if key in value and type(value[key]) is not bool:
            raise ValueError(f"{key} must be true or false")
        result[key] = value.get(key, False)
    return result


def save_settings(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)

