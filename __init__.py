"""Hermes plugin entry for the New Room connector."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hermes_new_room.plugin import register

__all__ = ["register"]
