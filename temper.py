"""Deterministic derivation: certificate plus state becomes a temperament.

The certificate is normative; the wording is a rendering of it. Nothing here
draws a seed, and nothing here lets a caller substitute a different one.
"""

from __future__ import annotations

from typing import Any

from . import cert as store

DEFAULT_REGISTRY = "core@0.3"
MAX_EVENT_CHARS = 500


class TemperamentError(RuntimeError):
    """A missing or inconsistent certificate, or a missing dependency."""


def _core():
    try:
        from exoself import core
    except ImportError as exc:  # pragma: no cover - dependency consent declined
        raise TemperamentError(
            "the exoself package is not installed in this Hermes runtime"
        ) from exc
    return core


def _render():
    try:
        from exoself import render
    except ImportError as exc:  # pragma: no cover
        raise TemperamentError(
            "the exoself package is not installed in this Hermes runtime"
        ) from exc
    return render


def registry_for(cert: dict[str, Any]):
    core = _core()
    return core.load_registry(name=cert.get("registry") or DEFAULT_REGISTRY)


def seed_of(cert: dict[str, Any]) -> bytes:
    return bytes.fromhex(cert["seed"])


def require_cert() -> dict[str, Any]:
    cert = store.load_cert()
    if not cert:
        raise TemperamentError(
            "no certificate in this profile; the operator draws one with `hermes exoself born`"
        )
    return cert


def aligned_state(cert: dict[str, Any], reg: dict[str, Any]) -> dict[str, Any]:
    """The stored state, or a fresh one when it belongs to another agent."""
    core = _core()
    state = store.load_state()
    if not state or state.get("id") != cert.get("id"):
        state = core.new_state(seed_of(cert), reg)
    return state


def snapshot(desire: bool = False) -> dict[str, Any]:
    """Verify the certificate and render the temperament it implies."""
    core = _core()
    render = _render()
    cert = require_cert()
    reg, reg_hash = registry_for(cert)
    problems = core.verify_certificate(cert, reg_hash)
    if problems:
        raise TemperamentError("certificate does not verify: " + "; ".join(problems))
    state = aligned_state(cert, reg)
    phenotype = core.phenotype(seed_of(cert), reg, state)
    return {
        "cert": cert,
        "registry": reg,
        "state": state,
        "phenotype": phenotype,
        "prompt": render.render_prompt(phenotype, reg, desire=desire),
        "soul": render.render_soul(phenotype, reg, desire=desire),
    }


def _apply(state: dict[str, Any], reg: dict[str, Any], cert: dict[str, Any],
           event: bytes, satisfied: tuple[str, ...]) -> dict[str, Any]:
    core = _core()
    new_state = core.develop(seed_of(cert), state, event, reg, satisfied=list(satisfied))
    store.write_json(store.state_path(), new_state)
    return new_state


def record_event(summary: str, satisfied: list[str] | None = None) -> dict[str, Any]:
    """Record one experience the agent chose to name."""
    cert = require_cert()
    reg, _ = registry_for(cert)
    text = " ".join(str(summary or "").split())[:MAX_EVENT_CHARS]
    if not text:
        raise TemperamentError("an event needs a short description of what happened")
    with store.locked():
        state = aligned_state(cert, reg)
        new_state = _apply(state, reg, cert, text.encode("utf-8"), tuple(satisfied or ()))
    return new_state


def record_turn(session_id: str, platform: str, reason: str,
                limit: int) -> dict[str, Any] | None:
    """Automatic development: one event per completed turn, bounded per session.

    The event carries turn facts only. No message text, argument or file path
    ever reaches the state file, and nothing here can be steered by the model.
    """
    cert = require_cert()
    reg, _ = registry_for(cert)
    event = f"turn:{platform or 'unknown'}:{reason or 'unknown'}".encode("utf-8")
    with store.locked():
        runtime = store.load_runtime()
        if runtime.get("session_id") != session_id:
            runtime = {"session_id": session_id, "events": 0}
        if int(runtime.get("events") or 0) >= max(0, int(limit)):
            return None
        state = aligned_state(cert, reg)
        new_state = _apply(state, reg, cert, event, ())
        runtime["events"] = int(runtime.get("events") or 0) + 1
        store.write_json(store.runtime_path(), runtime)
    return new_state
