from binascii import Error
from pathlib import Path
import base64
import json
import re
import requests
import sys


def dump_alias(plain_text:bool =False):
    appdata_path = get_settings_path()

    try:
        with open(appdata_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return "Error: Settings file not found. Have you run the game yet?"

    if plain_text:
        return json.dumps(data.get('cmd_alias', {}), indent=2)
    else:
        aliases = data.get('cmd_alias', {})
        return base64.b64encode(json.dumps(aliases).encode('utf-8')).decode('utf-8')

def get_settings_path():
    home = Path.home()
    if sys.platform == "win32":
        base = home / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    elif sys.platform == "linux":
        base = home / ".local" / "share"
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")

    return base / 'godot' / 'app_userdata' / 'Tower Networking Inc' / 'settings.json'

def get_user_input():
    try:
        user_input = input(': ').lower()
    except KeyboardInterrupt:
        sys.exit()
    return user_input

def load_base64_string():
    user_input = input('Paste the Base64 encoded string here: ')
    try:
        decoded_json = base64.b64decode(user_input.encode('utf-8')).decode('utf-8')
        new_aliases = json.loads(decoded_json)
    except (Error, json.JSONDecodeError):
        print('Error: Data provided is not valid Base64 or JSON.')
        return

    print("Preview of aliases to import:")
    print(json.dumps(new_aliases, indent=2))

    write_to_file(new_aliases)

def load_file(filename: Path):
    return json.load(open(filename, 'r'))

def load_library():
    file_list = []
    
    if not Path('library').exists():
        Path('library').mkdir()

    for root, dirs, files in Path('library').walk():
        for file in files:
            if file.endswith('.json'):
                file_list.append(file)
                
    if not file_list:
        print("No library files found. Try running [5] Pull libraries first.")
        return

    while True:
        for i, file in enumerate(file_list, start=1):
            print(f"[{i}] {file}")
        print('[Q] Go Back')
        user_input = get_user_input()

        if user_input.lower() in ['', 'q']:
            break
            
        try:
            selection_index = int(user_input) - 1
            if 0 <= selection_index < len(file_list):
                filename = Path('library') / file_list[selection_index]
                
                # Just load the JSON directly
                data = load_file(filename)
                
                print("\nPreview of aliases to import:")
                print(json.dumps(data, indent=4))

                if write_to_file(data):
                    break
            else:
                print("Invalid number.")
        except ValueError:
            print("Please enter a number.")

def pull_new_files():
    if not Path('library').exists():
        Path('library').mkdir()

    session = requests.Session()
    print("Checking for updates from GitHub...")
    try:
        url = "https://api.github.com/repos/iiEpic/tower-networking-alias-manager/git/trees/97891c53c3e21eb61614c1b1043b96de53765b8b?recursive=1"
        response = session.get(url)
        data = response.json()

        for file in [i for i in data.get("tree", []) if i['path'].startswith('library/')]:
            file_response = session.get(file['url'])
            blob_data = file_response.json()

            raw_file_content = base64.b64decode(blob_data['content']).decode('utf-8')
            
            final_json = {}
            local_filename = Path('library') / file['path'].replace('library/', '')

            if local_filename.suffix == '.txt':
                try:
                    final_json = json.loads(base64.b64decode(raw_file_content).decode('utf-8'))
                    local_filename = local_filename.with_suffix('.json')
                except Exception as e:
                    print(f"Skipping {local_filename}: Invalid Base64 string.")
                    continue

            elif local_filename.suffix == '.json':
                try:
                    final_json = json.loads(raw_file_content)
                except json.JSONDecodeError:
                    continue

            with open(local_filename, 'w+') as f:
                json.dump(final_json, f, indent=4)
                
        print('Successfully updated library files.')
        
    except Exception as e:
        print(f'Error updating library: {e}')

def write_to_file(new_aliases: dict):
    confirm = input('Overwriting your current aliases with these. Are you sure? [Y/n]: ')
    if confirm.lower() in ['', 'y', 'ye', 'yes']:
        appdata_path = get_settings_path()

        try:
            with open(appdata_path, 'r') as f:
                full_settings = json.load(f)
        except FileNotFoundError:
            print("Error: Could not find settings file.")
            return

        full_settings['cmd_alias'] = new_aliases

        with open(appdata_path, 'w') as f:
            json.dump(full_settings, f, indent=4)

        print('Success! Aliases updated.')
        return True
    else:
        print("Cancelled.")
        return False

def main():
    # library = pull_new_files()

    while True:
        print('\n---[ Tower Networking Inc Alias Modifier ]---')
        print('[1] View current alias (Plain Text)')
        print('[2] Dump current alias (Base64 for sharing)')
        print('[3] Load a Base64 string')
        print('[4] Load from library')
        print('[5] Pull libraries from Github')
        print('[Q] Quit')

        user_input = get_user_input()

        if user_input == '1':
            print("\n" + dump_alias(plain_text=True))
        elif user_input == '2':
            print("\nCopy this string:")
            print(dump_alias())
        elif user_input == '3':
            load_base64_string()
        elif user_input == '4':
            load_library()
        elif user_input == '5':
            pull_new_files()
        elif user_input.lower() in ['', 'q']:
            break

if __name__ == '__main__':
    main()
