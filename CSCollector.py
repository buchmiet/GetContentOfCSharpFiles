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
from pathlib import Path
import PySimpleGUI as sg

def scan_folder(path, patterns=('*.cs', '*.csproj')):
    """
    Przeszukuje rekurencyjnie dany folder w poszukiwaniu plików pasujących
do wzorców i zwraca listę słowników z kluczem 'file' i 'content'.
    """
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
            if os.path.isdir(folder):
                new_items = scan_folder(folder)
                if new_items:
                    data.extend(new_items)
                    window['-JSON-'].update(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    sg.popup('Brak plików .cs lub .csproj w wybranym folderze.')
            else:
                sg.popup_error('Nieprawidłowa ścieżka do folderu')

        elif event == 'Wyczyść':
            data.clear()
            window['-JSON-'].update('')

    window.close()


if __name__ == '__main__':
    main()
