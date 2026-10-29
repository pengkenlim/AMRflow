"""Visualization helpers for AMRflow."""

from __future__ import annotations


def render_summary(data: dict) -> dict:
    """Return a simple summary representation for downstream plotting."""
    return {"status": "ok", "rows": len(data) if isinstance(data, dict) else 0}
