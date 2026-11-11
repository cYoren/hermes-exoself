"""The system prompt section: a drawn temperament, frozen per session.

Hermes freezes plugin sections into each new session prompt and persists the
rendered text, so the block a model reads is the block that was computed for
that session. The section is bounded and fails open: a broken certificate
removes the block, it never breaks a session.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping

from . import temper

logger = logging.getLogger(__name__)

SECTION_ID = "exoself.temperament"
MAX_CHARS = 3000

PREAMBLE = (
    "# Temperament\n\n"
    "This is a temperament drawn from a certificate, not a persona written by anyone. "
    "It shapes manner only. The operating contract above wins on every conflict, "
    "including length, tone, authority, approval gates and report format."
)


def build_text(desire: bool) -> str:
    snap = temper.snapshot(desire=desire)
    return (PREAMBLE + "\n\n" + snap["prompt"]).strip()


def register_prompt_section(ctx) -> None:
    def content(_session_info: Mapping[str, Any]) -> str:
        try:
            desire = bool(ctx.get_config("desire", default=False))
            return build_text(desire)[:MAX_CHARS]
        except temper.TemperamentError as exc:
            logger.debug("exoself: no temperament section: %s", exc)
            return ""
        except Exception:  # pragma: no cover - never break a session over a persona
            logger.warning("exoself: could not render the temperament section", exc_info=True)
            return ""

    ctx.register_system_prompt_section(SECTION_ID, content, position="after_memory", max_chars=MAX_CHARS)
