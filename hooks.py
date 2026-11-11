"""Session hook: the agent grows from turns it actually lived.

``on_session_end`` fires once per turn. The event recorded here is derived from
turn facts (platform, exit reason), never from message text, so growth cannot be
steered by anything the model writes and no conversation content is persisted.
"""

from __future__ import annotations

import logging

from . import temper

logger = logging.getLogger(__name__)


def _int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def register_hooks(ctx) -> None:
    def on_session_end(
        completed: bool = False,
        failed: bool = False,
        interrupted: bool = False,
        session_id: str = "",
        platform: str = "",
        turn_exit_reason: str = "",
        **_extra: object,
    ) -> None:
        if not completed or failed or interrupted:
            return
        if not bool(ctx.get_config("auto_record", default=True)):
            return
        limit = _int(ctx.get_config("max_events_per_session", default=20), 20)
        try:
            temper.record_turn(
                session_id=str(session_id or ""),
                platform=str(platform or ""),
                reason=str(turn_exit_reason or ""),
                limit=limit,
            )
        except temper.TemperamentError as exc:
            logger.debug("exoself: no development recorded: %s", exc)
        except Exception:  # pragma: no cover - a bookkeeping failure never fails the turn
            logger.warning("exoself: development hook failed", exc_info=True)

    ctx.register_hook("on_session_end", on_session_end)
