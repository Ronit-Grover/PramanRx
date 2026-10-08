from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(
        os.getenv("PRAMANRX_DB_PATH", PROJECT_ROOT / "data/runtime/pramanrx.sqlite3")
    )
    kb_path: Path = Path(
        os.getenv("PRAMANRX_KB_PATH", PROJECT_ROOT / "data/compiled/kb-v1.json")
    )
    kb_signature_path: Path = Path(
        os.getenv("PRAMANRX_KB_SIGNATURE_PATH", PROJECT_ROOT / "data/compiled/kb-v1.sig")
    )
    public_key_path: Path = Path(
        os.getenv("PRAMANRX_PUBLIC_KEY_PATH", PROJECT_ROOT / "data/compiled/pramanrx-ed25519-public.pem")
    )
    private_key_path: Path = Path(
        os.getenv("PRAMANRX_PRIVATE_KEY_PATH", PROJECT_ROOT / "data/runtime/pramanrx-ed25519-private.pem")
    )
    ollama_url: str = os.getenv("PRAMANRX_OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("PRAMANRX_OLLAMA_MODEL", "llama3.2:3b")
    external_ai_url: str | None = os.getenv("PRAMANRX_EXTERNAL_AI_URL")
    external_ai_token: str | None = os.getenv("PRAMANRX_EXTERNAL_AI_TOKEN")


settings = Settings()
