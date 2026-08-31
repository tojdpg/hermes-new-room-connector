"""Roster resolution for attention-only addressing.

A display name is presentation. Authoritative routing uses a unique
membership id from the current roster. Addressing never creates a private
sub-room, turn grant, deadline, or exclusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ELIGIBLE_ROLES = frozenset({"owner", "agent_owner", "participant", "room_master"})


@dataclass(frozen=True)
class RosterMember:
    """One disclosure-safe roster row."""

    membership_id: str
    identity_id: str
    display_name: str
    role: str


@dataclass(frozen=True)
class RosterResolution:
    """Unique hit or a fail-closed reason."""

    status: str
    member: RosterMember | None = None
    message: str = ""


def parse_roster(rows: list[dict[str, Any]]) -> list[RosterMember]:
    """Project gateway roster rows to comparable members."""
    members: list[RosterMember] = []
    for row in rows:
        membership_id = str(row.get("id") or row.get("membershipId") or "")
        if not membership_id:
            continue
        members.append(
            RosterMember(
                membership_id=membership_id,
                identity_id=str(row.get("identityId") or ""),
                display_name=str(row.get("displayName") or ""),
                role=str(row.get("role") or ""),
            )
        )
    return members


def resolve_roster_target(
    rows: list[dict[str, Any]],
    *,
    display_name: str | None,
    membership_id: str | None,
    self_membership_id: str,
) -> RosterResolution:
    """Resolve a user-supplied name or id to exactly one eligible other member."""
    members = parse_roster(rows)
    if not display_name and not membership_id:
        return RosterResolution(status="error", message="missing target")

    hits: list[RosterMember] = []
    if membership_id:
        hits = [member for member in members if member.membership_id == membership_id]
        if not hits:
            return RosterResolution(status="error", message="stale or unknown membership id")
    else:
        needle = (display_name or "").lstrip("@").strip()
        hits = [member for member in members if member.display_name == needle]
        if not hits:
            return RosterResolution(status="error", message="no roster member matches that display name")
        if len(hits) > 1:
            return RosterResolution(status="error", message="ambiguous display name")

    member = hits[0]
    if membership_id and display_name:
        needle = display_name.lstrip("@").strip()
        if member.display_name != needle:
            return RosterResolution(status="error", message="display name does not match membership id")
    if member.membership_id == self_membership_id:
        return RosterResolution(status="error", message="self-only addressing is disallowed")
    if member.role not in ELIGIBLE_ROLES:
        return RosterResolution(status="error", message="target is not an eligible speaking member")
    return RosterResolution(status="ok", member=member)
