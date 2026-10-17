"""Shared helpers for agent modules."""

from __future__ import annotations


def strip_fences(text: str) -> str:
    """Strip markdown code fences Gemini sometimes wraps around JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def format_volume(vol: float) -> str:
    if vol >= 1e9:
        return f"${vol / 1e9:.1f}B"
    if vol >= 1e6:
        return f"${vol / 1e6:.1f}M"
    return f"${vol:,.0f}"
