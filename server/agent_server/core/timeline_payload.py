"""Trim inline base64 image data from timeline responses.

Tool results can embed images as base64. A single screenshot is often a few
hundred kilobytes, and the connector stores the same bytes in several content
fields, so one page of timeline history can reach several megabytes. Clients
render the tool text and preview, not the raw bytes, so replace base64 runs at
the response boundary while keeping item structure and metadata intact.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_server.core.models import TimelineItem

_INLINE_IMAGE_HINTS = (
    "iVBORw0KGgo",  # PNG
    "/9j/",  # JPEG
    "R0lGOD",  # GIF
    "UklGR",  # WebP
    "data:image/",
    '"type": "base64"',
    '"type":"base64"',
)
_BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{4096,}")
_MIN_INLINE_IMAGE_CHARS = 8192
_PLACEHOLDER = "[inline image data omitted]"


def strip_inline_image_data(items: list[TimelineItem]) -> list[TimelineItem]:
    """Return timeline items with large inline base64 images replaced."""
    return [
        item.model_copy(
            update={"content": strip_inline_image_content(item.content)}
        )
        if item.type == "tool"
        else item
        for item in items
    ]


def strip_inline_image_content(value: Any) -> Any:
    """Recursively replace base64 image blocks with a short placeholder."""
    if isinstance(value, dict):
        if value.get("type") == "base64" and isinstance(value.get("data"), str):
            data = value["data"]
            if len(data) >= _MIN_INLINE_IMAGE_CHARS:
                return {**value, "data": _PLACEHOLDER, "omittedBytes": len(data)}
        return {key: strip_inline_image_content(item) for key, item in value.items()}
    if isinstance(value, list):
        return [strip_inline_image_content(item) for item in value]
    if isinstance(value, str) and len(value) >= _MIN_INLINE_IMAGE_CHARS:
        return _strip_inline_image_string(value)
    return value


def _strip_inline_image_string(value: str) -> str:
    if not any(hint in value for hint in _INLINE_IMAGE_HINTS):
        return value
    return _BASE64_RUN.sub(_PLACEHOLDER, value)
