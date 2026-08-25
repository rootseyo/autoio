"""Macro storage in the operating system's per-user data directory."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path

from .events import load_macro, write_macro

INVALID_FILENAME = re.compile(r"[<>:\"/\\|?*\x00-\x1f]")
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{n}" for n in range(1, 10)),
    *(f"LPT{n}" for n in range(1, 10)),
}


def default_macro_directory() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "AutoIO" / "macros"
    if system == "Windows":
        roaming = os.environ.get("APPDATA")
        base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
        return base / "rootseyo" / "AutoIO" / "macros"
    xdg_data = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data) if xdg_data else Path.home() / ".local" / "share"
    return base / "autoio" / "macros"


def safe_macro_name(name: str) -> str:
    cleaned = INVALID_FILENAME.sub("_", name).strip().rstrip(".")
    if cleaned.lower().endswith(".json"):
        cleaned = cleaned[:-5].rstrip(". ")
    if not cleaned or cleaned.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        raise ValueError("Please enter a valid macro name.")
    return cleaned[:100]


class MacroStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory else default_macro_directory()
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, name: str) -> Path:
        return self.directory / f"{safe_macro_name(name)}.json"

    def list(self) -> list[Path]:
        return sorted(self.directory.glob("*.json"), key=lambda path: path.name.casefold())

    def save(self, name: str, events: list[dict]) -> Path:
        path = self.path_for(name)
        write_macro(path, events)
        return path

    def load(self, path: Path) -> list[dict]:
        return load_macro(path)

    def import_file(self, source: Path) -> Path:
        events = load_macro(source)
        destination = self.path_for(source.stem)
        write_macro(destination, events)
        return destination

    def delete(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved.parent != self.directory.resolve() or resolved.suffix.lower() != ".json":
            raise ValueError("Refusing to delete a file outside the macro directory.")
        resolved.unlink()
