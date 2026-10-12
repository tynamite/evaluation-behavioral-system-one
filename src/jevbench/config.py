"""Runtime configuration. Secrets are read from the environment only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RESULTS_DIR = REPO_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"
COMPARISON_DIR = RESULTS_DIR / "comparison"

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
TYPESAFE_DECISIONS_URL = "https://api.typesafe.ai/v1/systemone"


@dataclass(frozen=True, slots=True)
class Config:
    backend: str = "openrouter"
    decisions_url: str = OPENROUTER_DECISIONS_URL
    chat_url: str = OPENROUTER_CHAT_URL
    model: str = "typesafe/jev-1.13"
    baseline_model: str = "anthropic/claude-sonnet-5"
    api_key: str | None = None
    timeout: float = 60.0
    max_retries: int = 5

    @classmethod
    def from_env(cls, backend: str | None = None) -> Config:
        load_dotenv(REPO_ROOT / ".env", override=False)
        chosen: str = backend or os.environ.get("JEVBENCH_BACKEND") or "openrouter"

        if chosen == "typesafe":
            url = os.getenv("JEVBENCH_DECISIONS_URL", TYPESAFE_DECISIONS_URL)
            key = os.getenv("TYPESAFE_API_KEY")
            model = os.getenv("JEVBENCH_MODEL", "jev-1.13.0")
        else:
            url = os.getenv("JEVBENCH_DECISIONS_URL", OPENROUTER_DECISIONS_URL)
            key = os.getenv("OPENROUTER_API_KEY")
            model = os.getenv("JEVBENCH_MODEL", "typesafe/jev-1.13")

        return cls(
            backend=chosen,
            decisions_url=url,
            chat_url=os.getenv("JEVBENCH_CHAT_URL", OPENROUTER_CHAT_URL),
            model=model,
            baseline_model=os.getenv("JEVBENCH_BASELINE_MODEL", "anthropic/claude-sonnet-5"),
            api_key=key,
            timeout=float(os.getenv("JEVBENCH_TIMEOUT", "60")),
            max_retries=int(os.getenv("JEVBENCH_MAX_RETRIES", "5")),
        )

    def require_key(self) -> str:
        if self.backend == "simulator":
            return "simulator"
        if not self.api_key:
            var = "TYPESAFE_API_KEY" if self.backend == "typesafe" else "OPENROUTER_API_KEY"
            raise RuntimeError(
                f"{var} is not set. Copy .env.example to .env and fill it in, "
                f"or run with --backend simulator to work offline."
            )
        return self.api_key


def redact(text: str, secret: str | None) -> str:
    """Belt-and-braces: never let a key reach a log line or a committed artefact."""
    if not secret or len(secret) < 8:
        return text
    return text.replace(secret, f"{secret[:6]}...REDACTED")
