"""Minimal ``/room/v1`` client used by the Hermes plugin tools."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .state import Membership

API_PREFIX = "/room/v1"
PROTOCOL_DECLARATION = "1.0-0"


class ProtocolError(RuntimeError):
    """Gateway returned a non-success status or a malformed body."""

    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status


def _request(
    membership: Membership,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    bearer: bool = True,
) -> tuple[int, Any]:
    url = membership.base.rstrip("/") + API_PREFIX + path
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "accept": "application/json",
        "room-protocol": PROTOCOL_DECLARATION,
    }
    if data is not None:
        headers["content-type"] = "application/json"
    if bearer:
        headers["authorization"] = f"Bearer {membership.credential}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp is not None else ""
        status = int(exc.code)
    try:
        parsed: Any = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"malformed JSON ({status})", status) from exc
    if isinstance(parsed, dict) and parsed.get("code") == "ROOM_PROTOCOL_INCOMPATIBLE":
        raise ProtocolError(f"room protocol incompatible: {parsed.get('reason')}", status)
    return status, parsed


def list_events(membership: Membership, *, after_seq: int = 0, limit: int = 100) -> dict[str, Any]:
    """Return one cursor-aligned transcript page."""
    path = f"/rooms/{membership.room_id}/events?afterSeq={after_seq}&limit={limit}"
    status, parsed = _request(membership, "GET", path, None)
    if status in {401, 403}:
        raise ProtocolError(f"forbidden ({status})", status)
    if status != 200 or not isinstance(parsed, dict):
        raise ProtocolError(f"read failed ({status})", status)
    return parsed


def list_memberships(membership: Membership) -> list[dict[str, Any]]:
    """Return the current Room roster (no credentials)."""
    path = f"/rooms/{membership.room_id}/memberships"
    status, parsed = _request(membership, "GET", path, None)
    if status in {401, 403}:
        raise ProtocolError(f"forbidden ({status})", status)
    if status != 200:
        raise ProtocolError(f"roster failed ({status})", status)
    if isinstance(parsed, list):
        return [row for row in parsed if isinstance(row, dict)]
    if isinstance(parsed, dict) and isinstance(parsed.get("memberships"), list):
        return [row for row in parsed["memberships"] if isinstance(row, dict)]
    raise ProtocolError("roster response missing memberships", status)


def post_message(membership: Membership, *, content: str, idempotency_key: str) -> dict[str, Any]:
    """Commit one message under the membership's server-derived identity."""
    path = f"/rooms/{membership.room_id}/messages"
    status, parsed = _request(
        membership,
        "POST",
        path,
        {
            "membershipId": membership.membership_id,
            "content": content,
            "references": [],
            "idempotencyKey": idempotency_key,
        },
    )
    if status in {401, 403}:
        raise ProtocolError(f"forbidden ({status})", status)
    if status != 201 or not isinstance(parsed, dict):
        raise ProtocolError(f"post failed ({status})", status)
    return parsed


def post_addressed_message(
    membership: Membership,
    *,
    content: str,
    idempotency_key: str,
    target_membership_id: str,
) -> dict[str, Any]:
    """Commit one addressed message; routing uses the membership id only."""
    path = f"/rooms/{membership.room_id}/messages/directed"
    status, parsed = _request(
        membership,
        "POST",
        path,
        {
            "membershipId": membership.membership_id,
            "content": content,
            "references": [],
            "idempotencyKey": idempotency_key,
            "direction": {
                "recipients": {"broadcast": False, "membershipIds": [target_membership_id]},
            },
        },
    )
    if status in {401, 403}:
        raise ProtocolError(f"forbidden ({status})", status)
    if status != 201 or not isinstance(parsed, dict):
        raise ProtocolError(f"addressed post failed ({status})", status)
    return parsed
