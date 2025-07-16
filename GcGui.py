# -*- coding: utf-8 -*-
"""
PathManagerApp 2.0
------------------
Minimalistyczne GUI (Textual) + pipeline zbierający *.cs / *.csproj
i kopiujący wynikowy JSON do schowka.

Autor: Twój pierwotny kod + logika scalona przez ChatGPT
"""
import os
import json
import uuid
import re
from pathlib import Path

import pyperclip                        # operacje na schowku
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, ListView, Label, Static
from textual.reactive import reactive
from textual.message import Message

DEFAULT_PATTERN_STRING = "*.cs;*.csproj;*.props*;*.md"

def parse_patterns(pattern_string: str) -> list[str]:
    """Return patterns list split on ';' or ','."""
    return [p.strip() for p in re.split(r"[;,]+", pattern_string) if p.strip()]


# ---------- DOMAIN / SERVICE LAYER ---------- #
class PathProcessor:
    """Single-responsibility service: agreguje dane folderów."""

    patterns = parse_patterns(DEFAULT_PATTERN_STRING)

    @classmethod
    def update_patterns(cls, pattern_string: str) -> None:
        cls.patterns = parse_patterns(pattern_string) or parse_patterns(DEFAULT_PATTERN_STRING)

    @classmethod
    def _read_file(cls, file_path: Path) -> str | None:
        """Próbuje odczytać plik w UTF-8 lub fallback latin-1."""
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return file_path.read_text(encoding="latin-1")
            except Exception:
                return None

    @classmethod
    def scan_folder(cls, dir_path: str) -> dict | None:
        """Zwraca FolderDto albo None, jeżeli brak pasujących plików."""
        p = Path(dir_path)
        if not p.is_dir():
            return None

        files_with_content: dict[str, str] = {}
        for pattern in cls.patterns:
            for fp in p.rglob(pattern):
                if fp.is_file():
                    content = cls._read_file(fp)
                    if content is not None:
                        files_with_content[fp.name] = content

        if not files_with_content:
            return None

        return {"Path": str(p.resolve()), "FilesWithContent": files_with_content}

    @classmethod
    def collect(cls, roots: list[str]) -> tuple[list[dict], int]:
        """Zwraca (lista folderów, łączna liczba plików)."""
        folders: list[dict] = []
        total_files = 0
        for root in roots:
            dto = cls.scan_folder(root)
            if dto:
                total_files += len(dto["FilesWithContent"])
                folders.append(dto)
        return folders, total_files


# ---------- PRESENTATION LAYER (GUI) ---------- #
class PathItem(Static):
    """Pojedynczy wiersz na liście ścieżek."""

    path = reactive("")

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.item_uuid = str(uuid.uuid4())

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.path, classes="path-label")
            yield Button(
                "Remove",
                variant="error",
                id=f"remove_{self.item_uuid}",
                classes="remove-button",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if getattr(event.button, "id", None) == f"remove_{self.item_uuid}":
            self.post_message(PathItem.Removed(self.path))
            self.remove()

    class Removed(Message):
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path


class PathManagerApp(App):
    """GUI: zarządzanie ścieżkami + wywołanie pipeline."""

    CSS = """
    Screen {
        overflow: hidden;
    }
    #paths-container {
        width: 100%;
        height: 65%;
        border: round green;
        padding: 1;
        margin-bottom: 1;
        overflow-y: auto;
    }
    #controls-container {
        width: 100%;
        height: 35%;
        min-height: 7;
        border: round blue;
        padding: 1;
        grid-size: 2;
        grid-gutter: 1 0;
    }
    #pattern-row { width: 100%; height: 3; align-vertical: middle; }
    #pattern-input { width: 1fr; margin-right: 1; height: 100%; }
    .pattern-label { width: auto; margin-right: 1; }
    #input-row { width: 100%; height: 3; align-vertical: middle; }
    #path-input { width: 1fr; margin-right: 1; height: 100%; }
    #get-path { width: auto; min-width: 10; }
    #bottom-buttons { width: 100%; height: 3; }
    #generate, #exit { width: 1fr; min-width: 10; }
    #exit { margin-left: 1; }
    PathItem { margin: 0; height: 1; }
    .path-label { width: 1fr; content-align: left middle; margin-right: 1; height: 1; }
    .remove-button { width: auto; min-width: 8; height: 1; content-align: center middle; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    # ---------- UI COMPOSITION ---------- #
    def compose(self) -> ComposeResult:
        with Container(id="paths-container"):
            yield Label("Paths:")
            self.path_list = ListView(id="path-list")
            yield self.path_list

        with Container(id="controls-container"):
            with Horizontal(id="pattern-row"):
                yield Label("Patterns:", classes="pattern-label")
                yield Input(DEFAULT_PATTERN_STRING, id="pattern-input")
            with Horizontal(id="input-row"):
                yield Input(placeholder="Wprowadź ścieżkę…", id="path-input")
                yield Button("Get Path", id="get-path", variant="primary")
            with Horizontal(id="bottom-buttons"):
                yield Button("Generate", id="generate", variant="success")
                yield Button("Exit", id="exit", variant="error")

    def on_mount(self) -> None:
        self.query_one("#path-input").focus()

    # ---------- EVENT HANDLERS ---------- #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = getattr(event.button, "id", None)

        if button_id == "get-path":
            self._handle_add_path()
        elif button_id == "generate":
            self._handle_generate()
        elif button_id == "exit":
            self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "path-input":
            self._handle_add_path(from_input=event.input)

    def on_path_item_removed(self, message: PathItem.Removed) -> None:
        try:
            self.paths.remove(message.path)
            self.notify(f"Removed: {message.path}")
        except ValueError:
            self.notify(f"Not found: {message.path}", title="Error", severity="error")

    # ---------- COMMAND METHODS ---------- #
    def _handle_add_path(self, from_input: Input | None = None) -> None:
        inp = from_input or self.query_one("#path-input")
        raw_path = inp.value.strip()

        if not raw_path:
            self.notify("Path cannot be empty.", title="Warning", severity="warning")
            inp.focus()
            return

        # Visual Studio allows easy copying of the *.csproj file path.  If such
        # a path is provided, treat its parent directory as the target folder.
        path = raw_path
        if raw_path.lower().endswith(".csproj") and os.path.isfile(raw_path):
            path = os.path.dirname(raw_path)

        if path in self.paths:
            self.notify(f"'{path}' already exists.", title="Warning", severity="warning")
        elif not os.path.isdir(path):
            self.notify(f"'{raw_path}' is not a directory.", title="Error", severity="error")
        else:
            self._add_path(path)
            self.notify(f"Added: {path}", severity="information")
            inp.value = ""
        inp.focus()

    def _add_path(self, path: str) -> None:
        self.paths.append(path)
        item = PathItem(path)
        self.path_list.append(item)
        self.call_after_refresh(self.path_list.scroll_to_widget, item, animate=False)

    def _handle_generate(self) -> None:
        """Główna akcja 'Generate' – uruchamia pipeline i kopiuje JSON do schowka."""
        if not self.paths:
            self.notify("No paths to process.", title="Info", severity="information")
            return

        pattern_str = self.query_one("#pattern-input").value
        PathProcessor.update_patterns(pattern_str)

        folders, total_files = PathProcessor.collect(self.paths)

        if not folders:
            self.notify("No matching files found.", title="Info", severity="information")
            return

        json_payload = json.dumps(folders, indent=4, ensure_ascii=False)
        try:
            pyperclip.copy(json_payload)
            self.notify(
                f"Copied {len(folders)} folder(s), {total_files} file(s) to clipboard.",
                title="Success",
                severity="information",
            )
        except Exception as e:
            self.log.error(f"Clipboard error: {e}")
            self.notify(f"Clipboard error: {e}", title="Error", severity="error")


# ---------- ENTRY POINT ---------- #
if __name__ == "__main__":
    PathManagerApp().run()
