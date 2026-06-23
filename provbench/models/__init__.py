"""Model adapters — vendor-neutral. A model is just `complete(prompt) -> str | None`.

- claude_cli: shells out to the `claude` CLI (`claude -p`), using a logged-in Claude Code
  subscription — no API key, no per-token billing. What we use to run the benchmark.
- (API adapters for Anthropic/OpenAI keys can be added with the same signature; anyone running
  the benchmark plugs in their own.)

Everything fails CLOSED: a missing CLI, a non-zero exit, or a timeout returns None, and the
caller treats None as "no judgement" rather than a pass.
"""

from collections.abc import Callable

from .claude_cli import available, claude_cli_model, complete

# A model is just: prompt -> text reply, or None on any failure (fail closed).
ModelFn = Callable[[str], "str | None"]

__all__ = ["available", "claude_cli_model", "complete", "ModelFn"]
