"""Register New Room tools on a named Hermes profile.

Registration is network-free so ``hermes plugins doctor`` can load the plugin.
Tool handlers talk to ``/room/v1`` only after a membership exists in this
profile's private state. Sender identity is always the authenticated
membership; caller text cannot override it.
"""

from __future__ import annotations

import json
from typing import Any

from .cli import new_room_command, register_cli
from .protocol import ProtocolError, list_events, list_memberships, post_addressed_message, post_message
from .roster import resolve_roster_target
from .state import load_membership, profile_id, public_bindings, refuse_default_profile

PLUGIN_NAME = "new-room-connector"
PLUGIN_VERSION = "0.1.0-rc.6"

CONTEXT_SCHEMA: dict[str, Any] = {
    "name": "new_room_context",
    "description": (
        "Read a deterministic, cursor-aligned window of the current New Room "
        "transcript for this Hermes profile. Returns canonical public events "
        "in ascending sequence. Read-only. Never returns credentials."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "roomId": {
                "type": "string",
                "description": "The Room whose transcript context to read.",
            },
            "afterSeq": {
                "type": "integer",
                "description": "Exclusive cursor to read after; omit or 0 for the start.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum events to return (default 100).",
            },
        },
        "required": ["roomId"],
    },
}

POST_SCHEMA: dict[str, Any] = {
    "name": "new_room_post",
    "description": (
        "Publish one message to New Room under this profile's authenticated "
        "membership. Optional targetDisplayName is resolved against the live "
        "roster to exactly one eligible member; @DisplayName in the body is "
        "presentation only. Publishes exactly once under a frozen idempotency "
        "token. Never accepts a credential or actor override."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "roomId": {
                "type": "string",
                "description": "The Room to publish the message to.",
            },
            "content": {
                "type": "string",
                "description": "The message body to publish.",
            },
            "targetDisplayName": {
                "type": "string",
                "description": (
                    "Optional display name to resolve against the current roster. "
                    "Must match exactly one eligible other member."
                ),
            },
            "targetMembershipId": {
                "type": "string",
                "description": "Optional structured membership id to address. Must be unique and eligible.",
            },
            "idempotencyToken": {
                "type": "string",
                "description": "Optional stable token making retries idempotent.",
            },
        },
        "required": ["roomId", "content"],
    },
}


def _error(code: str, message: str) -> str:
    return json.dumps({"status": "error", "code": code, "message": message})


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"status": "ok", **payload})


def handle_new_room_context(url: str = "", afterSeq: int = 0, limit: int = 100, roomId: str = "", **_kwargs: Any) -> str:
    """Read one bounded transcript page for the calling profile."""
    room = roomId or url
    try:
        refuse_default_profile()
        membership = load_membership(profile_id(), room)
        if membership is None:
            return _error("unknown_membership", "this profile has no membership in that room")
        page = list_events(membership, after_seq=int(afterSeq or 0), limit=int(limit or 100))
        events = page.get("events") if isinstance(page.get("events"), list) else []
        return _ok({
            "roomId": room,
            "afterSeq": int(afterSeq or 0),
            "events": events,
            "nextCursor": page.get("nextCursor", afterSeq or 0),
            "truncated": bool(page.get("hasMore")),
        })
    except ProtocolError as exc:
        return _error("protocol_error", str(exc))
    except Exception as exc:
        return _error("internal_error", type(exc).__name__)


def handle_new_room_post(
    roomId: str = "",
    content: str = "",
    targetDisplayName: str = "",
    targetMembershipId: str = "",
    idempotencyToken: str = "",
    **_kwargs: Any,
) -> str:
    """Publish one message under the calling profile's membership identity."""
    try:
        refuse_default_profile()
        if not roomId or not content:
            return _error("invalid_arguments", "roomId and content are required")
        membership = load_membership(profile_id(), roomId)
        if membership is None:
            return _error("unknown_membership", "this profile has no membership in that room")
        target = None
        if targetDisplayName or targetMembershipId:
            roster = list_memberships(membership)
            resolved = resolve_roster_target(
                roster,
                display_name=targetDisplayName or None,
                membership_id=targetMembershipId or None,
                self_membership_id=membership.membership_id,
            )
            if resolved.status != "ok":
                return _error("target_unresolved", resolved.message)
            target = resolved.member
        token = idempotencyToken or f"newroom-post:{roomId}:{membership.membership_id}:{content}"
        if target is not None:
            token = f"{token}:{target.membership_id}"
        if target is not None:
            event = post_addressed_message(
                membership,
                content=content,
                idempotency_key=token,
                target_membership_id=target.membership_id,
            )
        else:
            event = post_message(membership, content=content, idempotency_key=token)
        result: dict[str, Any] = {
            "roomId": roomId,
            "seq": event.get("seq"),
            "idempotencyKey": token,
            "actorMembershipId": membership.membership_id,
        }
        if target is not None:
            result["target"] = {
                "membershipId": target.membership_id,
                "displayName": target.display_name,
            }
        return _ok(result)
    except ProtocolError as exc:
        status = getattr(exc, "status", 0)
        if status in {401, 403}:
            return _error("forbidden", str(exc))
        return _error("protocol_error", str(exc))
    except Exception as exc:
        return _error("internal_error", type(exc).__name__)


def _room_prompt(_info: Any = None, **_kwargs: Any) -> str:
    """Disclosure-safe Room membership summary for a new session. No secrets."""
    try:
        pid = profile_id()
        if pid == "default":
            return "New Room connector is installed. Use a named non-default profile to join."
        rows = public_bindings(pid)
        if not rows:
            return "New Room connector is installed. No Room membership is stored for this profile yet."
        rooms = ", ".join(str(row.get("roomId")) for row in rows)
        return f"This profile is a New Room member of: {rooms}. Use new_room_context and new_room_post."
    except Exception:
        return "New Room connector is installed."


def _on_pre_llm_call(**_kwargs: Any) -> None:
    """Inbound hook placeholder: registration-safe, no network."""
    return None


def register(ctx: Any) -> None:
    """Register the two New Room tools. Called by the Hermes plugin loader."""
    ctx.register_tool(
        name="new_room_context",
        toolset="new_room",
        schema=CONTEXT_SCHEMA,
        handler=handle_new_room_context,
        description=CONTEXT_SCHEMA["description"],
        emoji="📖",
    )
    ctx.register_tool(
        name="new_room_post",
        toolset="new_room",
        schema=POST_SCHEMA,
        handler=handle_new_room_post,
        description=POST_SCHEMA["description"],
        emoji="💬",
    )
    ctx.register_cli_command(
        name="new-room",
        help="Operate the New Room connector for this Hermes profile",
        setup_fn=register_cli,
        handler_fn=new_room_command,
        description="Status, doctor, pending, disable, uninstall, and rollback for New Room.",
    )
    ctx.register_system_prompt_section(
        "new-room-membership",
        _room_prompt,
        position="after_memory",
        max_chars=800,
    )
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
