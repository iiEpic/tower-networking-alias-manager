from binascii import Error
from pathlib import Path
import base64
import json
import sys


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

def load_alias():
    user_input = input('Paste the Base64 encoded string here: ')
    try:
        decoded_json = base64.b64decode(user_input.encode('utf-8')).decode('utf-8')
        new_aliases = json.loads(decoded_json)
    except (Error, json.JSONDecodeError):
        print('Error: Data provided is not valid Base64 or JSON.')
        return

    print("Preview of aliases to import:")
    print(json.dumps(new_aliases, indent=2))

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
    else:
        print("Cancelled.")

def main():
    while True:
        print('\n---[ Tower Networking Inc Alias Modifier ]---')
        print('[1] View current alias (Plain Text)')
        print('[2] Dump current alias (Base64 for sharing)')
        print('[3] Load a Base64 string')
        print('[Q] Quit')

        try:
            user_input = input(': ').lower()
        except KeyboardInterrupt:
            sys.exit()

        if user_input == '1':
            print("\n" + dump_alias(plain_text=True))
        elif user_input == '2':
            print("\nCopy this string:")
            print(dump_alias())
        elif user_input == '3':
            load_alias()
        elif user_input.lower() in ['', 'q']:
            break

if __name__ == '__main__':
    main()
