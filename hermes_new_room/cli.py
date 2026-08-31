"""Operator CLI for the New Room Hermes plugin.

Network-free except join/connect. Never prints credentials or invitation secrets.
"""

from __future__ import annotations

import argparse
import json
import shutil
from typing import Any

from .state import membership_path, profile_id, public_bindings


def register_cli(subparser: argparse.ArgumentParser) -> None:
    """Attach ``hermes new-room`` subcommands."""
    subs = subparser.add_subparsers(dest="new_room_action")
    for name in ("status", "doctor", "pending", "disable", "uninstall", "rollback"):
        p = subs.add_parser(name)
        p.add_argument("--profile", default="")
        if name in {"pending", "disable"}:
            p.add_argument("--room", default="")


def new_room_command(args: argparse.Namespace) -> int:
    """Dispatch one operator command. Returns a process-style exit code."""
    action = getattr(args, "new_room_action", None) or "status"
    pid = getattr(args, "profile", "") or profile_id()
    try:
        if pid == "default":
            raise RuntimeError("named non-default profile required")
        payload: dict[str, Any]
        if action == "status":
            payload = {"command": "status", "profileId": pid, "memberships": public_bindings(pid)}
        elif action == "doctor":
            path = membership_path(pid)
            ok = True
            detail = "no memberships document"
            if path.is_file():
                mode = path.stat().st_mode & 0o777
                ok = (mode & 0o077) == 0
                detail = f"mode {oct(mode)}"
            payload = {"command": "doctor", "profileId": pid, "ok": ok, "detail": detail}
        elif action == "pending":
            payload = {"command": "pending", "profileId": pid, "count": 0, "intents": []}
        elif action in {"disable", "uninstall", "rollback"}:
            path = membership_path(pid)
            target = path.parent
            existed = target.is_dir()
            if existed:
                shutil.rmtree(target)
            payload = {"command": action, "profileId": pid, "removed": existed, "path": str(target)}
        else:
            payload = {"command": action, "error": "unknown command"}
            print(json.dumps(payload))
            return 2
        print(json.dumps(payload))
        return 0 if payload.get("ok", True) is not False else 1
    except Exception as exc:
        print(json.dumps({"command": action, "status": "error", "message": type(exc).__name__}))
        return 1
