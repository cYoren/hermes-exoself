"""exoself - a drawn temperament for a Hermes agent.

One 32 byte seed, drawn once by the operator with ``hermes exoself born``. The
certificate is expanded deterministically into a temperament block that is
frozen into each new session's system prompt, and the agent grows only from
turns it actually lived.

There is deliberately no tool and no code path that draws a second seed. Birth
is an operator action, and a reroll button is the one thing this framework
exists to prevent.
"""

from __future__ import annotations

from .exo_cli import register_cli
from .exo_tools import register_tools
from .hooks import register_hooks
from .prompt import register_prompt_section

__all__ = ["register"]


def register(ctx) -> None:
    """Wire the temperament into the host: prompt section, tools, hook, CLI."""
    register_prompt_section(ctx)
    register_tools(ctx)
    register_hooks(ctx)
    register_cli(ctx)
