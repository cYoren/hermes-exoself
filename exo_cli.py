"""Operator commands: ``hermes exoself born|show|status|verify|develop|path``.

Birth is here and only here. ``born`` creates the certificate with O_EXCL, so a
second draw in the same profile fails instead of silently replacing an agent.
"""

from __future__ import annotations

import json
import sys

from . import cert as store
from . import temper

USAGE = """hermes exoself <action>

  born      draw the seed for this profile, once, and render the temperament
  show      print the temperament (--format prompt|soul|json)
  status    handle, certificate id, sessions lived, appetites
  verify    recompute the certificate against its registry
  develop   record an experience (--event "..." [--satisfied drive])
  path      print the certificate and state paths
"""


def _fail(message: str) -> int:
    print(f"exoself: {message}", file=sys.stderr)
    return 1


def _born(_args) -> int:
    path = store.cert_path()
    if path.exists():
        return _fail(
            f"{path} already exists. An agent is born once per profile; "
            "refusing to draw a second seed. Delete the file only if you mean to replace the agent."
        )
    core = temper._core()
    reg, reg_hash = core.load_registry(name=temper.DEFAULT_REGISTRY)
    seed = __import__("secrets").token_bytes(core.SEED_BYTES)
    cert = core.born(reg_hash, registry_name=temper.DEFAULT_REGISTRY, seed=seed)
    store.create_exclusive(path, cert)
    state = core.new_state(seed, reg)
    store.write_json(store.state_path(), state)
    pheno = core.phenotype(seed, reg, state)
    print(f"{pheno['handle']} ({pheno['id']})")
    print(f"  certificate  {path}")
    print(f"  state        {store.state_path()}")
    print("  the temperament is now part of this profile's next session prompt")
    return 0


def _show(args) -> int:
    try:
        snap = temper.snapshot(desire=bool(getattr(args, "desire", False)))
    except temper.TemperamentError as exc:
        return _fail(str(exc))
    fmt = getattr(args, "format", "prompt") or "prompt"
    if fmt == "json":
        print(json.dumps(snap["phenotype"], indent=2, sort_keys=True))
    elif fmt == "soul":
        sys.stdout.write(snap["soul"])
    else:
        sys.stdout.write(snap["prompt"])
    return 0


def _status(_args) -> int:
    try:
        snap = temper.snapshot()
    except temper.TemperamentError as exc:
        return _fail(str(exc))
    pheno, state = snap["phenotype"], snap["state"]
    print(f"{pheno['handle']} ({pheno['id']}). Sessions recorded: {state.get('events', 0)}.")
    print(f"Certificate: {store.cert_path()}")
    for d in pheno.get("drives", []):
        print(f"{d['drive']}: {d['state']}")
    if pheno.get("fixation"):
        print(f"fixation: {pheno['fixation']}")
    return 0


def _verify(_args) -> int:
    core = temper._core()
    try:
        cert = temper.require_cert()
        _reg, reg_hash = temper.registry_for(cert)
    except temper.TemperamentError as exc:
        return _fail(str(exc))
    problems = core.verify_certificate(cert, reg_hash)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print("ok")
    return 0


def _develop(args) -> int:
    event = getattr(args, "event", None)
    if not event:
        return _fail('develop needs --event "what happened"')
    try:
        state = temper.record_event(event, list(getattr(args, "satisfied", []) or []))
    except temper.TemperamentError as exc:
        return _fail(str(exc))
    print(f"recorded. sessions: {state.get('events', 0)}")
    return 0


def _path(_args) -> int:
    print(store.cert_path())
    print(store.state_path())
    return 0


_ACTIONS = {
    "born": _born,
    "show": _show,
    "status": _status,
    "verify": _verify,
    "develop": _develop,
    "path": _path,
}


def setup_parser(parser) -> None:
    parser.add_argument("action", nargs="?", default="status", choices=sorted(_ACTIONS))
    parser.add_argument("--format", choices=["prompt", "soul", "json"], default="prompt")
    parser.add_argument("--desire", action="store_true", help="include appetites")
    parser.add_argument("--event", help="experience to record (develop)")
    parser.add_argument("--satisfied", action="append", default=[], help="drive id satisfied (develop)")


def handle(args) -> int:
    action = getattr(args, "action", "status") or "status"
    handler = _ACTIONS.get(action)
    if handler is None:
        print(USAGE, file=sys.stderr)
        return 2
    return handler(args)


def register_cli(ctx) -> None:
    ctx.register_cli_command(
        name="exoself",
        help="Draw, inspect and develop this profile's temperament",
        description=USAGE,
        setup_fn=setup_parser,
        handler_fn=handle,
    )
