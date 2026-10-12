import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    env_file = BACKEND_ROOT / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value and key not in os.environ:
            os.environ[key] = value


load_local_env()


def env_value(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default
