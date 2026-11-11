from __future__ import annotations

from typing import Any

from agent_server.core.models import TimelineItem, TimelineSource
from agent_server.core.timeline_payload import (
    strip_inline_image_content,
    strip_inline_image_data,
)

_IMAGE_BYTES = "iVBORw0KGgo" + "A" * 9000


def _item(content: dict[str, Any], item_type: str = "tool") -> TimelineItem:
    return TimelineItem(
        id="item-1",
        sessionId="sess-1",
        type=item_type,  # type: ignore[arg-type]
        status="done",
        role="tool",
        content=content,
        source=TimelineSource(runtime="claude"),
        orderSeq=1,
        revision=1,
        contentHash="sha256:test",
        createdAt="2026-01-01T00:00:00Z",
        updatedAt="2026-01-01T00:00:00Z",
        updatedSeq=1,
    )


def test_replaces_structured_base64_image_data() -> None:
    stripped = strip_inline_image_content(
        {
            "result": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": _IMAGE_BYTES,
                    },
                }
            ]
        }
    )

    source = stripped["result"][0]["source"]
    assert source["data"] == "[inline image data omitted]"
    assert source["media_type"] == "image/png"
    assert source["omittedBytes"] == len(_IMAGE_BYTES)


def test_replaces_base64_runs_inside_output_strings() -> None:
    output = (
        '[{"type":"text","text":"read ok"},'
        '{"type":"image","source":{"type":"base64","data":"'
        + _IMAGE_BYTES
        + '"}}]'
    )

    stripped = strip_inline_image_content({"output": output})

    assert "read ok" in stripped["output"]
    assert _IMAGE_BYTES not in stripped["output"]
    assert "[inline image data omitted]" in stripped["output"]


def test_keeps_small_and_plain_strings() -> None:
    assert strip_inline_image_content({"output": "hello"}) == {"output": "hello"}

    long_text = "x" * 9000
    assert strip_inline_image_content({"output": long_text}) == {"output": long_text}


def test_strip_inline_image_data_only_rewrites_tool_items() -> None:
    tool_item = _item({"output": _IMAGE_BYTES})
    message_item = _item({"text": _IMAGE_BYTES}, item_type="message")

    stripped = strip_inline_image_data([tool_item, message_item])

    assert _IMAGE_BYTES not in stripped[0].content["output"]
    assert stripped[1] is message_item
    assert tool_item.content["output"] == _IMAGE_BYTES
