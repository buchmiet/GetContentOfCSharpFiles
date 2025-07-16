#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
from pathlib import Path

# --- Stałe ---
DEFAULT_CONTENT_FILENAME = "content.json"
CONFIG_FILENAME = ".script_config.json" # Plik do zapamiętania ostatniej ścieżki (ukryty)

# --- Funkcje pomocnicze ---

def load_config(config_dir):
    """Wczytuje zapamiętaną ścieżkę z pliku konfiguracyjnego."""
    config_path = os.path.join(config_dir, CONFIG_FILENAME)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                return config_data.get("last_content_dir")
        except json.JSONDecodeError:
            print(f"Ostrzeżenie: Plik konfiguracyjny '{config_path}' jest uszkodzony. Zostanie zignorowany.")
        except IOError as e:
            print(f"Ostrzeżenie: Nie można odczytać pliku konfiguracyjnego '{config_path}': {e}")
    return None

def save_config(config_dir, content_dir):
    """Zapisuje ścieżkę do pliku konfiguracyjnego."""
    config_path = os.path.join(config_dir, CONFIG_FILENAME)
    config_data = {"last_content_dir": content_dir}
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        print(f"Zapamiętano ścieżkę '{content_dir}' w pliku konfiguracyjnym '{config_path}'.")
    except IOError as e:
        print(f"Błąd: Nie można zapisać pliku konfiguracyjnego '{config_path}': {e}")

def determine_content_path(arg_path, remembered_path):
    """Określa ścieżkę do pliku content.json."""
    if arg_path:
        print(f"Używam ścieżki podanej w argumencie: '{arg_path}'")
        # Zapisujemy jako nową zapamiętaną ścieżkę
        save_config(os.path.dirname(os.path.abspath(__file__)), arg_path) # Zapisz w katalogu skryptu
        return os.path.join(arg_path, DEFAULT_CONTENT_FILENAME)
    elif remembered_path:
        print(f"Używam zapamiętanej ścieżki: '{remembered_path}'")
        return os.path.join(remembered_path, DEFAULT_CONTENT_FILENAME)
    else:
        current_dir = os.getcwd()
        print(f"Brak argumentu i zapamiętanej ścieżki. Używam bieżącego katalogu: '{current_dir}'")
        return os.path.join(current_dir, DEFAULT_CONTENT_FILENAME)

def load_folders(filepath):
    """Wczytuje istniejącą kolekcję folderów z pliku JSON."""
    if os.path.exists(filepath):
        print(f"Znaleziono istniejący plik: '{filepath}'. Próbuję wczytać dane...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Sprawdzenie czy plik nie jest pusty
                content = f.read()
                if not content.strip():
                    print("Plik jest pusty. Zaczynam z nową kolekcją.")
                    return []
                # Resetowanie wskaźnika pliku po odczycie
                f.seek(0)
                data = json.load(f)
                if isinstance(data, list):
                    print(f"Wczytano {len(data)} istniejących wpisów.")
                    return data
                else:
                    print("Błąd: Oczekiwano listy obiektów w pliku JSON, znaleziono inny format. Tworzę nową kolekcję.")
                    return []
        except json.JSONDecodeError as e:
            print(f"Błąd: Niepoprawny format JSON w pliku '{filepath}': {e}. Tworzę nową kolekcję.")
            return []
        except IOError as e:
            print(f"Błąd: Nie można odczytać pliku '{filepath}': {e}. Tworzę nową kolekcję.")
            return []
    else:
        print(f"Plik '{filepath}' nie istnieje. Zostanie utworzony nowy.")
        return []

def save_folders(filepath, folders):
    """Zapisuje kolekcję folderów do pliku JSON."""
    try:
        # Upewnij się, że katalog docelowy istnieje
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(folders, f, indent=4, ensure_ascii=False) # indent=4 dla czytelności
        print(f"Zapisano {len(folders)} wpisów do pliku: '{filepath}'")
        return True
    except IOError as e:
        print(f"Błąd: Nie można zapisać danych do pliku '{filepath}': {e}")
        return False
    except Exception as e:
        print(f"Błąd: Wystąpił nieoczekiwany błąd podczas zapisu do pliku '{filepath}': {e}")
        return False


def process_directory(dir_path):
    """Przetwarza podany katalog, znajdując pliki *.cs i *.csproj."""
    print(f"\n--- Przetwarzanie katalogu: '{dir_path}' ---")
    if not os.path.isdir(dir_path):
        print(f"Błąd: Podana ścieżka '{dir_path}' nie jest prawidłowym katalogiem.")
        return None

    files_with_content = {}
    # Używamy Path z pathlib dla łatwiejszego tworzenia wzorców glob
    p = Path(dir_path)
    patterns = ['*.cs', '*.csproj']
    found_files_count = 0

    for pattern in patterns:
        try:
            # glob.glob szuka tylko w bieżącym katalogu, rglob rekurencyjnie
            # Użyjemy p.glob(pattern) do wyszukiwania tylko w podanym folderze
            for file_path in p.rglob(pattern):
                if file_path.is_file(): # Upewnijmy się, że to plik
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Kluczem w słowniku jest nazwa pliku, wartością jego zawartość
                        files_with_content[file_path.name] = content
                        found_files_count += 1
                        print(f"  + Odczytano plik: {file_path.name}")
                    except UnicodeDecodeError:
                         print(f"  ! Ostrzeżenie: Nie można odczytać pliku '{file_path.name}' z kodowaniem UTF-8. Próbuję latin-1...")
                         try:
                             with open(file_path, 'r', encoding='latin-1') as f:
                                 content = f.read()
                             files_with_content[file_path.name] = content
                             found_files_count += 1
                             print(f"    + Odczytano plik (latin-1): {file_path.name}")
                         except Exception as e_inner:
                             print(f"  ! Błąd: Nie można odczytać pliku '{file_path.name}' nawet jako latin-1: {e_inner}")
                    except IOError as e:
                        print(f"  ! Błąd: Nie można odczytać pliku '{file_path.name}': {e}")
                    except Exception as e:
                         print(f"  ! Błąd: Nieoczekiwany błąd podczas przetwarzania pliku '{file_path.name}': {e}")

        except Exception as e:
             print(f"Błąd: Wystąpił błąd podczas wyszukiwania plików wzorca '{pattern}' w '{dir_path}': {e}")


    if not files_with_content:
        print("Nie znaleziono pasujących plików (*.cs, *.csproj) w tym katalogu.")
        return None # Zwracamy None, jeśli nic nie znaleziono

    folder_data = {
        "Path": os.path.abspath(dir_path), # Zapisujemy pełną ścieżkę
        "FilesWithContent": files_with_content
    }
    print(f"Zakończono przetwarzanie katalogu. Znaleziono {found_files_count} plików.")
    return folder_data


# --- Główna logika skryptu ---
def main():
    parser = argparse.ArgumentParser(description="Przetwarza foldery, zbierając zawartość plików *.cs i *.csproj do pliku JSON.")
    parser.add_argument("output_dir", nargs='?', default=None,
                        help="Opcjonalna ścieżka do katalogu, gdzie ma być zapisany/odczytany plik " + DEFAULT_CONTENT_FILENAME +
                             ". Jeśli nie podana, używana jest ostatnio zapamiętana ścieżka lub bieżący katalog.")

    args = parser.parse_args()

    print("--- Uruchomienie skryptu ---")

    # Wczytaj zapamiętaną ścieżkę z katalogu, w którym znajduje się skrypt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    remembered_path = load_config(script_dir)

    # Określ ścieżkę do pliku content.json
    content_json_path = determine_content_path(args.output_dir, remembered_path)
    content_dir = os.path.dirname(content_json_path) # Katalog, w którym jest content.json

    print(f"Plik wynikowy będzie zarządzany w: '{content_json_path}'")

    # Wczytaj istniejące dane (lub zainicjuj pustą listę)
    all_folders_data = load_folders(content_json_path)

    # Pętla pytająca użytkownika o foldery
    while True:
        try:
            user_input = input("\nPodaj ścieżkę do folderu do przetworzenia (lub zostaw puste i naciśnij Enter, aby zakończyć): ").strip()
            if not user_input:
                print("\nNie podano ścieżki. Kończenie pracy.")
                break

            # Sprawdź czy podana ścieżka jest poprawna
            if not os.path.exists(user_input):
                 print(f"Błąd: Ścieżka '{user_input}' nie istnieje. Spróbuj ponownie.")
                 continue
            if not os.path.isdir(user_input):
                 print(f"Błąd: Ścieżka '{user_input}' nie jest katalogiem. Spróbuj ponownie.")
                 continue


            new_folder_data = process_directory(user_input)

            if new_folder_data:
                # Dodaj nowe dane do istniejącej kolekcji
                all_folders_data.append(new_folder_data)
                print(f"Dodano dane dla folderu '{user_input}' do kolekcji.")

                # Zapisz zaktualizowaną kolekcję
                if save_folders(content_json_path, all_folders_data):
                     print("Kolekcja została pomyślnie zaktualizowana.")
                else:
                     print("Wystąpił błąd podczas zapisu. Dane z ostatniej operacji mogły nie zostać zapisane.")
            else:
                print(f"Nie przetworzono folderu '{user_input}' (brak plików lub błąd).")


        except KeyboardInterrupt:
             print("\nPrzerwano przez użytkownika (Ctrl+C). Kończenie pracy.")
             break
        except Exception as e:
             print(f"\n!! Wystąpił nieoczekiwany błąd w głównej pętli: {e}")
             print("Spróbuj ponownie lub zakończ działanie.")


    print("\n--- Zakończono działanie skryptu ---")

if __name__ == "__main__":
    main()