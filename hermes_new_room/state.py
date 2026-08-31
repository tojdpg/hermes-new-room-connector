"""Private per-profile membership lookup for the Hermes plugin.

Credentials stay in the owner-only document written by
``dsh-new-room-connector join``. This module never logs them.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


@dataclass(frozen=True)
class Membership:
    """Room membership plus bearer credential loaded from private state."""

    base: str
    room_id: str
    membership_id: str
    identity_id: str
    role: str
    credential: str


class StateError(RuntimeError):
    """Private state is missing, unsafe, or the profile id is invalid."""


def profile_id() -> str:
    """Resolve the named Hermes profile this plugin is running under."""
    explicit = os.environ.get("NEW_ROOM_PROFILE_ID")
    if explicit:
        return explicit
    home = os.environ.get("HERMES_HOME")
    if home:
        name = Path(home).name
        if name and name not in {".hermes", "hermes"}:
            return name
    return "default"


def refuse_default_profile() -> None:
    """The connector mounts only on a named non-default profile."""
    if profile_id() == "default":
        raise StateError("new-room-connector refuses the default Hermes profile")


def dsh_home() -> Path:
    """Harness home that roots New Room private state."""
    override = os.environ.get("DSH_HOME")
    if override:
        return Path(override)
    return Path.home() / ".dsh"


def membership_path(pid: str) -> Path:
    """Absolute path of one profile's private memberships document."""
    import re

    if not re.match(PROFILE_ID_PATTERN, pid):
        raise StateError(f"invalid profile id {pid!r}")
    return dsh_home() / "new-room" / "profiles" / pid / "memberships.json"


def load_membership(pid: str, room_id: str) -> Membership | None:
    """Load one room binding. Returns None when the profile has not joined."""
    path = membership_path(pid)
    if not path.is_file():
        return None
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise StateError(f"memberships document must be owner-only, found {oct(mode)}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    bindings = raw.get("bindings") if isinstance(raw, dict) else None
    if not isinstance(bindings, dict):
        return None
    record = bindings.get(room_id)
    if not isinstance(record, dict):
        return None
    return Membership(
        base=str(record["base"]),
        room_id=str(record["roomId"]),
        membership_id=str(record["membershipId"]),
        identity_id=str(record["identityId"]),
        role=str(record["role"]),
        credential=str(record["credential"]),
    )


def public_bindings(pid: str) -> list[dict[str, Any]]:
    """Disclosure-safe membership projections (no credentials)."""
    path = membership_path(pid)
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    bindings = raw.get("bindings") if isinstance(raw, dict) else {}
    out: list[dict[str, Any]] = []
    if not isinstance(bindings, dict):
        return out
    for record in bindings.values():
        if not isinstance(record, dict):
            continue
        out.append({
            "roomId": record.get("roomId"),
            "membershipId": record.get("membershipId"),
            "identityId": record.get("identityId"),
            "role": record.get("role"),
        })
    return out
