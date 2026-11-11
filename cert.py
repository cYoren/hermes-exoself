"""Certificate, state and runtime storage.

Everything lives in the profile's plugin data directory
(``<hermes home>/plugin-data/exoself/``), so it survives plugin updates and
belongs to exactly one Hermes home. A fleet therefore holds one certificate per
profile, and copying a home copies the agent.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

PLUGIN_ID = "exoself"
CERT_NAME = "birth.json"
STATE_NAME = "state.json"
RUNTIME_NAME = "runtime.json"
LOCK_NAME = ".lock"


def data_dir() -> Path:
    """Profile-scoped data directory, resolved per call so profiles never leak."""
    try:
        from plugins.plugin_storage import plugin_data_dir
    except ImportError:  # outside a Hermes runtime (tests, standalone harnesses)
        home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
        root = Path(home).expanduser() / "plugin-data" / PLUGIN_ID
        root.mkdir(parents=True, exist_ok=True)
        return root
    return plugin_data_dir(PLUGIN_ID)


def cert_path() -> Path:
    return data_dir() / CERT_NAME


def state_path() -> Path:
    return data_dir() / STATE_NAME


def runtime_path() -> Path:
    return data_dir() / RUNTIME_NAME


def _read(path: Path) -> dict[str, Any] | None:
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load_cert() -> dict[str, Any] | None:
    return _read(cert_path())


def load_state() -> dict[str, Any] | None:
    return _read(state_path())


def load_runtime() -> dict[str, Any]:
    return _read(runtime_path()) or {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomic replace, owner-readable only. A crash leaves the old file intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


def create_exclusive(path: Path, data: dict[str, Any]) -> None:
    """Create *path* only if it does not exist. A birth is never a reroll."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """Serialize read-modify-write on the state file across processes."""
    fd = os.open(str(data_dir() / LOCK_NAME), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.name == "nt":  # pragma: no cover - Windows has no flock
            import msvcrt

            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        with contextlib.suppress(OSError):
            if os.name == "nt":  # pragma: no cover
                import msvcrt

                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
