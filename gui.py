import customtkinter as ctk
import tkinter.messagebox as tkmb
from pathlib import Path
import json
import requests
import base64
import sys
import threading

# Set the theme for a professional "Network Engineer" aesthetic
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- GLOBAL HELPER FUNCTIONS ---

def get_settings_path():
    """Determines the correct path for Godot app data based on OS."""
    home = Path.home()
    if sys.platform == "win32":
        base = home / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    elif sys.platform == "linux":
        base = home / ".local" / "share"
    else:
        base = home / ".local" / "share"
        
    return base / 'godot' / 'app_userdata' / 'Tower Networking Inc' / 'settings.json'

def get_current_aliases():
    """Reads the current settings.json and returns the dict."""
    appdata_path = get_settings_path()
    try:
        with open(appdata_path, 'r') as f:
            data = json.load(f)
        return data.get('cmd_alias', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings_to_disk(new_aliases: dict):
    """Safely writes the new alias dict to settings.json."""
    appdata_path = get_settings_path()
    try:
        if appdata_path.exists():
            with open(appdata_path, 'r') as f:
                full_settings = json.load(f)
        else:
            full_settings = {}

        full_settings['cmd_alias'] = new_aliases
        
        # Ensure directory exists
        appdata_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(appdata_path, 'w') as f:
            json.dump(full_settings, f, indent=4)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- GUI FRAMES ---

class EditorFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=0) # List stays compact
        self.grid_columnconfigure(1, weight=1) # Editor expands
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT COLUMN: SEARCH & LIST ---
        self.left_container = ctk.CTkFrame(self, width=223, fg_color="transparent")
        self.left_container.grid(row=0, column=0, padx=0, sticky="nsew")
        self.left_container.grid_rowconfigure(2, weight=1) # List gets the space
        self.left_container.grid_propagate(False) 

        # 1. NEW: Add Button
        self.btn_add = ctk.CTkButton(self.left_container, text="+ New Alias", fg_color="#1f6aa5", command=self.add_alias_event)
        self.btn_add.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        # 2. Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self.update_search)
        self.entry_search = ctk.CTkEntry(self.left_container, placeholder_text="Search keys...", textvariable=self.search_var)
        self.entry_search.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")

        # 3. Scrollable Key List
        self.key_list_frame = ctk.CTkScrollableFrame(self.left_container, label_text="Alias Keys")
        self.key_list_frame.grid(row=2, column=0, sticky="nsew")

        # --- RIGHT COLUMN: VALUE EDITOR ---
        self.edit_container = ctk.CTkFrame(self)
        self.edit_container.grid(row=0, column=1, sticky="nsew")
        self.edit_container.grid_columnconfigure(0, weight=1)
        self.edit_container.grid_rowconfigure(1, weight=1)
        
        self.label_editing = ctk.CTkLabel(self.edit_container, text="Select a key to edit", font=ctk.CTkFont(weight="bold"))
        self.label_editing.grid(row=0, column=0, pady=10)

        self.val_textbox = ctk.CTkTextbox(self.edit_container, font=("Courier New", 14))
        self.val_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.btn_save = ctk.CTkButton(self.edit_container, text="Save Change", fg_color="#28a745", hover_color="#218838", command=self.save_entry_event)
        self.btn_save.grid(row=2, column=0, pady=20)

        self.all_aliases = {}
        self.selected_key = None

    def load_aliases(self):
        self.all_aliases = get_current_aliases()
        self.update_search()
        self.selected_key = None
        self.label_editing.configure(text="Select a key to edit", text_color="white")
        self.val_textbox.delete("0.0", "end")

    def update_search(self, *args):
        search_query = self.search_var.get().lower()
        
        for child in self.key_list_frame.winfo_children():
            child.destroy()
        self.button_map = {}
        
        for key in sorted(self.all_aliases.keys()):
            if search_query in key.lower():
                btn = ctk.CTkButton(self.key_list_frame, 
                                  text=key, 
                                  fg_color="transparent", 
                                  text_color=("gray10", "gray90"), 
                                  anchor="w", 
                                  command=lambda k=key: self.select_key(k))
                btn.pack(fill="x", padx=5, pady=2)
                
                self.button_map[key] = btn

    def select_key(self, key):
        self.selected_key = key
        
        # 3. Highlight Logic: Loop through map to update colors
        for k, btn in self.button_map.items():
            if k == key:
                btn.configure(fg_color="#1f6aa5") # Active Color
            else:
                btn.configure(fg_color="transparent") # Inactive Color

        self.label_editing.configure(text=f"Editing Alias: {key}", text_color="white")
        self.val_textbox.delete("0.0", "end")
        
        raw_value = self.all_aliases.get(key, "")
        if raw_value:
            # Convert semicolons to newlines for readable editing
            formatted_value = '\n'.join([i.strip() for i in raw_value.split(';') if i.strip()])
            self.val_textbox.insert("0.0", formatted_value)

    def add_alias_event(self):
        # Open a simple dialog to get the name
        dialog = ctk.CTkInputDialog(text="Enter name for new alias:", title="Create Alias")
        new_key = dialog.get_input()
        
        if new_key:
            new_key = new_key.strip()
            
            if new_key in self.all_aliases:
                tkmb.showerror("Error", "That alias already exists!")
                return
            
            if not new_key:
                return

            # Update Internal Dict
            self.all_aliases[new_key] = ""
            
            # Save to Disk immediately (so it persists)
            success, msg = save_settings_to_disk(self.all_aliases)
            
            if success:
                # Refresh list and select the new key
                self.update_search() 
                self.select_key(new_key)
                # Clear search so the new item definitely shows up
                self.search_var.set("")
            else:
                tkmb.showerror("Error", f"Could not create alias: {msg}")

    def save_entry_event(self):
        if not self.selected_key: return
        
        raw_text = self.val_textbox.get("0.0", "end-1c")
        clean_lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        new_value = ';'.join(clean_lines)
        
        self.all_aliases[self.selected_key] = new_value
        success, msg = save_settings_to_disk(self.all_aliases)
        
        if success:
            self.label_editing.configure(text=f"Saved: {self.selected_key}!", text_color="#28a745")
            self.after(2000, lambda: self.label_editing.configure(text=f"Editing Alias: {self.selected_key}", text_color="white"))
        else:
            self.label_editing.configure(text=f"Error: {msg}", text_color="red")

class LibraryFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.configure(corner_radius=0)
        self.grid_columnconfigure(0, weight=0) # File list
        self.grid_columnconfigure(1, weight=1) # Preview
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT: FILE LIST ---
        self.file_list_frame = ctk.CTkScrollableFrame(self, width=180, label_text="Available Libraries", fg_color="transparent")
        self.file_list_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- RIGHT: PREVIEW & IMPORT ---
        self.preview_container = ctk.CTkFrame(self)
        self.preview_container.grid(row=0, column=1, sticky="nsew")
        self.preview_container.grid_columnconfigure(0, weight=1)
        self.preview_container.grid_rowconfigure(1, weight=1)
        
        self.label_preview = ctk.CTkLabel(self.preview_container, text="Select a file to preview", font=ctk.CTkFont(weight="bold"))
        self.label_preview.grid(row=0, column=0, pady=10)

        self.preview_textbox = ctk.CTkTextbox(self.preview_container, font=("Courier New", 12))
        self.preview_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.preview_textbox.configure(state="disabled")

        self.btn_import = ctk.CTkButton(self.preview_container, text="Import This Library", state="disabled", fg_color="#d9534f", hover_color="#c9302c", command=self.import_event)
        self.btn_import.grid(row=2, column=0, pady=20)

        self.selected_file_data = None
        self.selected_filename = None

    def refresh_list(self):
        for child in self.file_list_frame.winfo_children():
            child.destroy()

        lib_path = Path('library')
        if not lib_path.exists():
            lib_path.mkdir()
            
        files = list(lib_path.glob('*.json'))
        if not files:
            lbl = ctk.CTkLabel(self.file_list_frame, text="No files found.\nSync GitHub first!")
            lbl.pack(pady=10)
            return

        for f in files:
            btn = ctk.CTkButton(self.file_list_frame, text=f.name, anchor="w", fg_color="transparent", border_width=1, text_color=("gray10", "gray90"), command=lambda x=f: self.select_file(x))
            btn.pack(fill="x", padx=5, pady=2)

    def select_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if 'plaintext' in data:
                self.selected_file_data = data['plaintext']
            else:
                self.selected_file_data = data
            
            self.selected_filename = filepath.name
            
            formatted_json = json.dumps(self.selected_file_data, indent=4)
            self.preview_textbox.configure(state="normal")
            self.preview_textbox.delete("0.0", "end")
            self.preview_textbox.insert("0.0", formatted_json)
            self.preview_textbox.configure(state="disabled")
            
            self.label_preview.configure(text=f"Previewing: {filepath.name}")
            self.btn_import.configure(state="normal", text=f"Overwrite Settings with {filepath.name}")

        except Exception as e:
            tkmb.showerror("Error", f"Could not read file: {e}")

    def import_event(self):
        if not self.selected_file_data: return
        
        if tkmb.askyesno("Confirm Overwrite", f"Are you sure you want to replace ALL current aliases with content from {self.selected_filename}?"):
            success, msg = save_settings_to_disk(self.selected_file_data)
            if success:
                tkmb.showinfo("Success", "Library imported successfully!")
            else:
                tkmb.showerror("Error", f"Failed to save: {msg}")

# --- MAIN APP ---

class TowerAliasManager(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Tower Networking Inc - Alias Manager")
        window_width = 1000
        window_height = 650
        
        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate x and y coordinates
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="THE FORGE", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_copy_b64 = ctk.CTkButton(self.sidebar_frame, text="Copy Base64 String", fg_color="#b97900", hover_color="#976200", command=self.copy_base64_event)
        self.btn_copy_b64.grid(row=1, column=0, padx=20, pady=10)

        self.btn_editor = ctk.CTkButton(self.sidebar_frame, text="Edit Current Alias", command=self.show_editor)
        self.btn_editor.grid(row=2, column=0, padx=20, pady=10)

        self.btn_library = ctk.CTkButton(self.sidebar_frame, text="Library Explorer", command=self.show_library)
        self.btn_library.grid(row=3, column=0, padx=20, pady=10)

        self.btn_view_b64 = ctk.CTkButton(self.sidebar_frame, text="View Base64 String", fg_color="#1f6aa5", command=self.view_base64_event)
        self.btn_view_b64.grid(row=4, column=0, padx=20, pady=10)

        self.btn_sync = ctk.CTkButton(self.sidebar_frame, text="Sync GitHub", command=self.sync_github)
        self.btn_sync.grid(row=5, column=0, padx=20, pady=10)

        # --- CONTENT FRAMES ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.editor_view = EditorFrame(self.main_container)
        self.library_view = LibraryFrame(self.main_container)

        self.status_label = ctk.CTkLabel(self, text="Application Ready", anchor="w")
        self.status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="we")

        self.show_editor()

    def copy_base64_event(self):
        """Generates Base64 string from current settings and copies to clipboard."""
        current_data = get_current_aliases()
        if not current_data:
            tkmb.showerror("Error", "No aliases found to copy!")
            return

        try:
            # 1. Convert dict to JSON string
            json_str = json.dumps(current_data)
            
            # 2. Encode to Base64
            b64_str = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            # 3. Copy to Clipboard
            self.clipboard_clear()
            self.clipboard_append(b64_str)
            self.update() # Required to finalize the clipboard event
            
            # 4. Notify User
            tkmb.showinfo("Copied!", "Base64 configuration string copied to clipboard.")
            self.status_label.configure(text="Copied Base64 string to clipboard.")
            
        except Exception as e:
            tkmb.showerror("Error", f"Failed to encode/copy: {e}")

    def show_editor(self):
        self.library_view.grid_forget()
        self.editor_view.grid(row=0, column=0, sticky="nsew")
        self.editor_view.load_aliases()
        self.status_label.configure(text="Editor Mode")

    def show_library(self):
        self.editor_view.grid_forget()
        self.library_view.grid(row=0, column=0, sticky="nsew")
        self.library_view.refresh_list()
        self.status_label.configure(text="Library Mode")

    def sync_github(self):
        self.status_label.configure(text="Contacting GitHub...")
        self.btn_sync.configure(state="disabled")
        threading.Thread(target=self._run_sync).start()

    def _run_sync(self):
        try:
            lib_path = Path('library')
            if not lib_path.exists(): lib_path.mkdir()

            session = requests.Session()
            url = "https://api.github.com/repos/iiEpic/tower-networking-alias-manager/git/trees/97891c53c3e21eb61614c1b1043b96de53765b8b?recursive=1"
            
            data = session.get(url).json()
            count = 0
            for file in [i for i in data.get("tree", []) if i['path'].startswith('library/')]:
                blob = session.get(file['url']).json()
                content = base64.b64decode(blob['content']).decode('utf-8')
                
                local_path = lib_path / file['path'].replace('library/', '')
                
                if local_path.suffix == '.txt':
                    try:
                        json_content = json.loads(base64.b64decode(content).decode('utf-8'))
                        local_path = local_path.with_suffix('.json')
                        with open(local_path, 'w') as f: json.dump(json_content, f, indent=4)
                        count += 1
                    except: pass
                elif local_path.suffix == '.json':
                    with open(local_path, 'w') as f: f.write(content)
                    count += 1

            self.after(0, lambda: self._sync_complete(f"Sync complete. Updated {count} files."))
        except Exception as e:
            self.after(0, lambda: self._sync_complete(f"Sync Failed: {str(e)}"))

    def _sync_complete(self, msg):
        self.status_label.configure(text=msg)
        self.btn_sync.configure(state="normal")
        if self.library_view.winfo_viewable():
            self.library_view.refresh_list()

    def view_base64_event(self):
        # Create Popup Window
        window = ctk.CTkToplevel(self)
        window.title("Base64 Viewer & Importer")
        window.geometry("600x650")
        window.transient(self) # Keep on top of main window
        
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(3, weight=1)

        # 1. Input
        lbl_in = ctk.CTkLabel(window, text="Paste Base64 String:", anchor="w", font=ctk.CTkFont(weight="bold"))
        lbl_in.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        txt_input = ctk.CTkTextbox(window, height=100)
        txt_input.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 2. Decode Button
        btn_decode = ctk.CTkButton(window, text="Decode & Preview", command=lambda: self._decode_b64(txt_input, txt_output, btn_import))
        btn_decode.grid(row=2, column=0, padx=20, pady=15)

        # 3. Output
        txt_output = ctk.CTkTextbox(window, font=("Courier New", 12))
        txt_output.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        txt_output.insert("0.0", "Waiting for input...")
        txt_output.configure(state="disabled")

        # 4. Import Button (Initially Disabled)
        btn_import = ctk.CTkButton(window, text="Import to Settings", state="disabled", fg_color="#d9534f", hover_color="#c9302c")
        btn_import.grid(row=4, column=0, padx=20, pady=20)

    def _decode_b64(self, in_widget, out_widget, import_btn):
        b64_text = in_widget.get("0.0", "end-1c").strip()
        if not b64_text: return

        out_widget.configure(state="normal")
        out_widget.delete("0.0", "end")
        
        try:
            # Attempt Decode
            json_str = base64.b64decode(b64_text).decode('utf-8')
            data = json.loads(json_str)
            
            # Show Pretty JSON
            out_widget.insert("0.0", json.dumps(data, indent=4))
            
            # Enable Import Button
            import_btn.configure(state="normal", command=lambda: self._import_b64_data(data, import_btn.winfo_toplevel()))
            
        except Exception as e:
            out_widget.insert("0.0", f"DECODE ERROR:\n{e}\n\nPlease check your string and try again.")
            import_btn.configure(state="disabled")
        
        out_widget.configure(state="disabled")

    def _import_b64_data(self, data, window):
        if tkmb.askyesno("Confirm Import", "This will overwrite your current aliases with the data above.\nAre you sure?"):
            success, msg = save_settings_to_disk(data)
            if success:
                tkmb.showinfo("Success", "Aliases imported successfully!")
                window.destroy() # Close popup
                if self.editor_view.winfo_viewable():
                    self.editor_view.load_aliases() # Refresh main UI
            else:
                tkmb.showerror("Error", f"Save failed: {msg}")

if __name__ == "__main__":
    app = TowerAliasManager()
    app.mainloop()