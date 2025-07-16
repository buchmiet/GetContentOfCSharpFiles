#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C# Collector GUI

Minimalna aplikacja desktopowa do zbierania zawartości plików .cs i .csproj
z wybranego folderu. Interfejs oparty na PySimpleGUI.

Aby zainstalować zależność:
    pip install PySimpleGUI

Użycie: uruchom ten skrypt, wybierz folder, kliknij "Dodaj". Zawartość JSON
pojawi się w polu poniżej. Możesz wyczyścić listę przyciskiem "Wyczyść".
"""
import json
import os
import re
from pathlib import Path
import PySimpleGUI as sg

DEFAULT_PATTERN_STRING = "*.cs;*.csproj;*.props*;*.md"

def parse_patterns(pattern_string: str) -> list[str]:
    """Split pattern string on ';' or ',' and return cleaned list."""
    return [p.strip() for p in re.split(r"[;,]+", pattern_string) if p.strip()]

DEFAULT_PATTERNS = parse_patterns(DEFAULT_PATTERN_STRING)


def scan_folder(path, patterns=None):
    """
    Przeszukuje rekurencyjnie dany folder w poszukiwaniu plików pasujących
do wzorców i zwraca listę słowników z kluczem 'file' i 'content'.
    """
    if patterns is None:
        patterns = DEFAULT_PATTERNS

    result = []
    base = Path(path)
    for pattern in patterns:
        for file_path in base.rglob(pattern):
            if file_path.is_file():
                try:
                    text = file_path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    text = file_path.read_text(encoding='latin-1', errors='ignore')
                result.append({
                    'file': str(file_path),
                    'content': text
                })
    return result


def main():
    sg.theme('LightBlue')  # Prosty motyw GUI

    layout = [
        [sg.Text('Ścieżka do folderu:'),
         sg.Input(key='-FOLDER-', enable_events=True),
         sg.FolderBrowse(button_text='Wybierz')],
        [sg.Text('Wildcardy:'),
         sg.Input(DEFAULT_PATTERN_STRING, key='-PATTERNS-')],
        [sg.Button('Dodaj', bind_return_key=True),
         sg.Button('Wyczyść'),
         sg.Button('Zamknij')],
        [sg.Multiline(size=(100, 25), key='-JSON-', autoscroll=True, font=('Consolas', 10))]
    ]

    window = sg.Window('C# Collector GUI', layout, resizable=True)
    data = []

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Zamknij'):
            break

        if event == 'Dodaj':
            folder = values['-FOLDER-']
            pattern_str = values.get('-PATTERNS-', DEFAULT_PATTERN_STRING)
            patterns = parse_patterns(pattern_str) or DEFAULT_PATTERNS
            if os.path.isdir(folder):
                new_items = scan_folder(folder, patterns)
                if new_items:
                    data.extend(new_items)
                    window['-JSON-'].update(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    sg.popup('Brak pasujących plików w wybranym folderze.')
            else:
                sg.popup_error('Nieprawidłowa ścieżka do folderu')

        elif event == 'Wyczyść':
            data.clear()
            window['-JSON-'].update('')

    window.close()


if __name__ == '__main__':
    main()
