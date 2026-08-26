"""Known-failure signatures mapped to readable errors.

The backend is frozen, so deployment defects the integration audit found
cannot be fixed at the source — but they can fail with an explanation
instead of a stack trace.
"""

from __future__ import annotations

# (substring of the error body, message returned instead)
_KNOWN_500S: tuple[tuple[str, str], ...] = (
    (
        "ai_detection_score",
        "This Promptmaxx instance is missing the AI-detection columns on "
        "generated_contents (known deployment defect F1: migration 0004 is "
        "state-only, so fresh databases never get the columns). Content "
        "tools work only against an instance where those columns exist — "
        "the corrective migration is content/0009, not yet committed.",
    ),
)


def readable_500(path: str, body: str) -> str | None:
    """Return a readable message for a recognized 500 body, else None."""
    for signature, message in _KNOWN_500S:
        if signature in body:
            return f"{path}: {message}"
    return None
