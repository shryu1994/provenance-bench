"""Run a model via the local `claude` CLI in headless print mode.

Uses the logged-in Claude Code subscription (no API key). Pure text in, text out; fails closed.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable


def available() -> bool:
    return shutil.which("claude") is not None


def complete(prompt: str, model: str = "haiku", timeout: int = 120) -> str | None:
    """Return the model's text reply, or None on any failure (fail closed)."""
    if not available():
        return None
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text", "--model", model],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def claude_cli_model(model: str = "haiku", timeout: int = 120) -> Callable[[str], "str | None"]:
    """A `complete`-shaped closure bound to one model name."""

    def _fn(prompt: str) -> str | None:
        return complete(prompt, model=model, timeout=timeout)

    return _fn
