"""Tools: read the temperament, verify the certificate, record experience.

There is no tool that draws a seed. Birth is an operator action taken through
``hermes exoself born``, and a tool that could redraw would be a reroll button.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import cert as store
from . import temper

logger = logging.getLogger(__name__)
TOOLSET = "exoself"

_STATUS = {
    "name": "exoself_status",
    "description": (
        "Report this agent's drawn temperament: handle, certificate id, sessions lived, "
        "and which appetites are present or hungry. Read-only and safe to call any time."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

_VERIFY = {
    "name": "exoself_verify",
    "description": (
        "Recompute this agent's certificate and compare it with the registry it names. "
        "Returns the identity problems, if any. Use it when you want to know whether the "
        "temperament you are reading is the one that was drawn."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

_TEMPERAMENT = {
    "name": "exoself_temperament",
    "description": (
        "Return the rendered temperament: the same text frozen into this session, or the "
        "Markdown persona, or the normative JSON phenotype. Use it to quote a trait exactly "
        "rather than paraphrasing yourself."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["prompt", "soul", "json"],
                "description": "prompt (session block), soul (Markdown persona), json (phenotype).",
            },
            "desire": {
                "type": "boolean",
                "description": "Include appetites. Default follows the plugin setting.",
            },
        },
        "additionalProperties": False,
    },
}

_RECORD = {
    "name": "exoself_record_session",
    "description": (
        "Record one experience that changed you, so the temperament develops from what "
        "actually happened. Use it at the end of real work, not for routine chatter. "
        "Name a drive the work satisfied only when it truly did."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "What happened, in one short sentence. No conversation content, no secrets.",
            },
            "satisfied": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Drive ids the event satisfied, e.g. ['teach', 'understand'].",
            },
        },
        "required": ["summary"],
        "additionalProperties": False,
    },
}


def _status(_args: dict[str, Any], **ctx_kw: Any) -> str:
    try:
        snap = temper.snapshot()
    except temper.TemperamentError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    cert, state, pheno = snap["cert"], snap["state"], snap["phenotype"]
    return json.dumps(
        {
            "ok": True,
            "handle": pheno.get("handle"),
            "id": pheno.get("id"),
            "registry": cert.get("registry"),
            "sessions": state.get("events", 0),
            "appetites": [
                {"drive": d.get("drive"), "state": d.get("state")} for d in pheno.get("drives", [])
            ],
            "fixation": pheno.get("fixation"),
            "certificate": str(store.cert_path()),
        }
    )


def _verify(_args: dict[str, Any], **ctx_kw: Any) -> str:
    try:
        core = temper._core()
        cert = temper.require_cert()
        _reg, reg_hash = temper.registry_for(cert)
        problems = core.verify_certificate(cert, reg_hash)
    except temper.TemperamentError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps({"ok": not problems, "id": cert.get("id"), "problems": problems})


def _temperament(args: dict[str, Any], **ctx_kw: Any) -> str:
    desire = args.get("desire")
    if not isinstance(desire, bool):
        desire = bool(ctx_kw.get("desire_default", False))
    fmt = str(args.get("format") or "prompt")
    try:
        snap = temper.snapshot(desire=desire)
    except temper.TemperamentError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    if fmt == "json":
        return json.dumps({"ok": True, "phenotype": snap["phenotype"]}, sort_keys=True)
    text = snap["soul"] if fmt == "soul" else snap["prompt"]
    return json.dumps({"ok": True, "format": fmt, "text": text})


def _record(args: dict[str, Any], **ctx_kw: Any) -> str:
    summary = str(args.get("summary") or "")
    satisfied = args.get("satisfied") or []
    if isinstance(satisfied, str):
        satisfied = [satisfied]
    try:
        state = temper.record_event(summary, [str(s) for s in satisfied])
    except temper.TemperamentError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps({"ok": True, "sessions": state.get("events", 0)})


def register_tools(ctx) -> None:
    for schema, handler in (
        (_STATUS, _status),
        (_VERIFY, _verify),
        (_TEMPERAMENT, _temperament),
        (_RECORD, _record),
    ):
        ctx.register_tool(name=schema["name"], toolset=TOOLSET, schema=schema, handler=handler)
