"""Versioned, portable macro event serialization."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_EVENTS = 1_000_000
MAX_FILE_BYTES = 50 * 1024 * 1024
EVENT_TYPES = {"mouse_move", "mouse_click", "mouse_scroll", "key_down", "key_up"}
MOUSE_BUTTONS = {"left", "middle", "right"}


class MacroFormatError(ValueError):
    """Raised when a macro file is malformed or unsupported."""


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MacroFormatError(f"'{field}' must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise MacroFormatError(f"'{field}' must be finite")
    return result


def _coordinate(value: Any, field: str) -> int:
    number = _number(value, field)
    if not number.is_integer():
        raise MacroFormatError(f"'{field}' must be an integer")
    return int(number)


def _key(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MacroFormatError("'key' must be an object")

    kind = value.get("kind", value.get("type"))
    if kind in {"special", "Key"}:
        name = value.get("name", value.get("value"))
        if not isinstance(name, str) or not name:
            raise MacroFormatError("special key name is missing")
        return {"kind": "special", "name": name}

    if kind in {"character", "KeyCode"}:
        char = value.get("char")
        vk = value.get("vk")
        if char is not None and not isinstance(char, str):
            raise MacroFormatError("key character must be a string or null")
        if vk is not None and (isinstance(vk, bool) or not isinstance(vk, int)):
            raise MacroFormatError("virtual key code must be an integer or null")
        if char is None and vk is None:
            raise MacroFormatError("character key must contain 'char' or 'vk'")
        return {"kind": "character", "char": char, "vk": vk}

    raise MacroFormatError(f"unsupported key kind: {kind!r}")


def normalize_event(raw: Any) -> dict[str, Any]:
    """Validate an event and convert legacy field names to schema v1."""
    if not isinstance(raw, dict):
        raise MacroFormatError("each event must be an object")

    legacy_types = {"m_move": "mouse_move", "m_click": "mouse_click", "m_scroll": "mouse_scroll"}
    event_type = legacy_types.get(raw.get("type"), raw.get("type"))
    if event_type not in EVENT_TYPES:
        raise MacroFormatError(f"unsupported event type: {event_type!r}")

    elapsed = _number(raw.get("time", raw.get("elapsed")), "time")
    if elapsed < 0:
        raise MacroFormatError("event time cannot be negative")

    event: dict[str, Any] = {"type": event_type, "time": elapsed}
    if event_type == "mouse_move":
        event.update(x=_coordinate(raw.get("x"), "x"), y=_coordinate(raw.get("y"), "y"))
    elif event_type == "mouse_click":
        button = raw.get("button")
        if button not in MOUSE_BUTTONS:
            raise MacroFormatError(f"unsupported mouse button: {button!r}")
        if not isinstance(raw.get("pressed"), bool):
            raise MacroFormatError("'pressed' must be true or false")
        event.update(
            x=_coordinate(raw.get("x"), "x"),
            y=_coordinate(raw.get("y"), "y"),
            button=button,
            pressed=raw["pressed"],
        )
    elif event_type == "mouse_scroll":
        event.update(
            x=_coordinate(raw.get("x"), "x"),
            y=_coordinate(raw.get("y"), "y"),
            dx=_coordinate(raw.get("dx"), "dx"),
            dy=_coordinate(raw.get("dy"), "dy"),
        )
    else:
        event["key"] = _key(raw.get("key"))
    return event


def describe_event(event: dict[str, Any]) -> str:
    """Return a compact Activity-log description for a normalized I/O event."""
    event_type = event["type"]
    if event_type == "mouse_move":
        return f"Mouse moved to ({event['x']}, {event['y']})"
    if event_type == "mouse_click":
        action = "down" if event["pressed"] else "up"
        return f"Mouse {event['button']} button {action} at ({event['x']}, {event['y']})"
    if event_type == "mouse_scroll":
        return f"Mouse scrolled dx={event['dx']}, dy={event['dy']} at ({event['x']}, {event['y']})"

    key = event["key"]
    if key["kind"] == "special":
        key_label = key["name"].upper()
    elif key.get("char") is not None:
        key_label = repr(key["char"])
    else:
        key_label = f"VK {key['vk']}"
    action = "down" if event_type == "key_down" else "up"
    return f"Keyboard {key_label} {action}"


def normalize_document(raw: Any) -> list[dict[str, Any]]:
    """Load a schema v1 document or the legacy bare event list."""
    if isinstance(raw, list):
        raw_events = raw
    elif isinstance(raw, dict):
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            raise MacroFormatError(f"unsupported schema version: {version!r}")
        raw_events = raw.get("events")
    else:
        raise MacroFormatError("macro root must be an object")

    if not isinstance(raw_events, list):
        raise MacroFormatError("'events' must be a list")
    if len(raw_events) > MAX_EVENTS:
        raise MacroFormatError(f"macro exceeds the {MAX_EVENTS:,} event limit")

    events = [normalize_event(item) for item in raw_events]
    previous = -1.0
    for event in events:
        if event["time"] < previous:
            raise MacroFormatError("event times must be in ascending order")
        previous = event["time"]
    return events


def make_document(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    normalized = normalize_document(list(events))
    return {"schema_version": SCHEMA_VERSION, "application": "AutoIO", "events": normalized}


def load_macro(path: Path) -> list[dict[str, Any]]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise MacroFormatError("macro file exceeds the 50 MB size limit")
        with path.open("r", encoding="utf-8") as file:
            return normalize_document(json.load(file))
    except MacroFormatError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise MacroFormatError(f"cannot read macro: {exc}") from exc


def write_macro(path: Path, events: Iterable[dict[str, Any]]) -> None:
    document = make_document(events)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(document, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
