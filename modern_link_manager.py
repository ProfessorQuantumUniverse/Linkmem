import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import webbrowser
import os
import re
import sys

# --- Konstanten ---
PROJECT_DIR_NAME = "LinkManager_Projects"

# --- HILFSKLASSEN (z.B. Dialoge) SOLLTEN HIER STEHEN ---
class LinkEntryDialog(simpledialog.Dialog):
    """Ein Dialog zum Hinzufügen oder Bearbeiten eines Links."""
    def __init__(self, parent, title="Link hinzufügen/bearbeiten", initial_data=None):
        self.initial_data = initial_data or {'url': '', 'desc': ''}
        self.result = None
        super().__init__(parent, title=title)

    def body(self, master):
        ttk.Label(master, text="URL:", anchor="w").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.url_entry.insert(0, self.initial_data.get('url', ''))

        ttk.Label(master, text="Beschreibung:", anchor="w").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.desc_entry = ttk.Entry(master, width=50)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.desc_entry.insert(0, self.initial_data.get('desc', ''))

        master.columnconfigure(1, weight=1)
        return self.url_entry

    def apply(self):
        url = self.url_entry.get().strip()
        desc = self.desc_entry.get().strip()

        if not url:
            messagebox.showwarning("Eingabe fehlt", "Die URL darf nicht leer sein.", parent=self)
            self.url_entry.focus_set()
            return

        if not url.startswith(("http://", "https://", "ftp://", "file://")):
             if not re.match(r"^[a-zA-Z]+://", url):
                 if messagebox.askyesno("URL-Format", f"Die URL '{url}' scheint kein Protokoll (z.B. http://) zu haben.\nSoll 'http://' vorangestellt werden?", parent=self):
                     url = "http://" + url

        if not desc:
            desc = url

        self.result = {'url': url, 'desc': desc}

class LinkManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Link Manager")
        self.root.minsize(650, 450)
        self.center_window(700, 500)

        self.project_dir = self.setup_project_directory()

        # Styling
        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        for theme in ['clam', 'alt', 'default']:
             if theme in available_themes:
                  self.style.theme_use(theme)
                  break
        self.style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))

        # Anwendungsstatus
        self.current_project_name = None
        self.current_project_path = None
        self.project_data = []
        self.unsaved_changes = False

        # --- Frames für die verschiedenen Ansichten ---
        self.container = ttk.Frame(root, padding="5")
        self.container.pack(fill=tk.BOTH, expand=True)

        self.start_frame = ttk.Frame(self.container, padding="10")
        self.project_frame = ttk.Frame(self.container, padding="10")

        # --- Seiteninhalte ERSTELLEN ---
        # WICHTIG: Erstelle die Widgets für BEIDE Seiten hier,
        # damit alle Attribute (wie self.link_tree) initialisiert sind.
        self.create_start_page_widgets()  # Erstellt self.project_tree etc.
        self.create_project_page_widgets() # Erstellt self.link_tree etc.

        # --- Globale Widgets (Statusleiste) ---
        # Wird jetzt hier erstellt, nicht mehr in create_project_page_widgets
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_status("Bereit.")

        # --- Initialansicht anzeigen ---
        self.show_frame(self.start_frame) # Zeige die Startseite

        # --- Schließen-Handler ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    def center_window(self, width=700, height=500):
        # ... (Code unverändert) ...
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.root.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def setup_project_directory(self):
        # ... (Code unverändert) ...
        docs_path = os.path.join(os.path.expanduser("~"), "Documents")
        proj_dir = os.path.join(docs_path, PROJECT_DIR_NAME)
        if not os.path.exists(docs_path):
             script_dir = os.getcwd() # Einfacherer Fallback
             # Für PyInstaller ist das komplexer, aber os.getcwd() ist oft ok
             try:
                 import sys
                 script_dir = os.path.dirname(os.path.realpath(sys.executable))
             except Exception:
                 script_dir = os.getcwd()
             proj_dir = os.path.join(script_dir, PROJECT_DIR_NAME)
        if not os.path.exists(proj_dir):
            try:
                os.makedirs(proj_dir)
                # Kein MessageBox hier, kann nerven. Loggen wäre besser.
                print(f"Info: Projektverzeichnis wurde erstellt: {proj_dir}")
            except OSError as e:
                messagebox.showerror("Fehler", f"Konnte Projektverzeichnis nicht erstellen:\n{proj_dir}\nFehler: {e}\n\nProjekte werden im aktuellen Verzeichnis gesucht/gespeichert.")
                proj_dir = "."
        return proj_dir


    def show_frame(self, frame_to_show):
        # ... (Code unverändert) ...
        for frame in [self.start_frame, self.project_frame]:
            frame.pack_forget()
        frame_to_show.pack(fill=tk.BOTH, expand=True)
        if frame_to_show == self.start_frame:
            self.root.title("Link Manager - Projektübersicht")
            self.load_projects_into_list()
        elif frame_to_show == self.project_frame:
             self.update_project_frame_title()

    # --- Startseite Widgets ---
    # Umbenannt von create_start_page zu create_start_page_widgets
    def create_start_page_widgets(self):
        self.start_frame.columnconfigure(0, weight=1)
        self.start_frame.rowconfigure(1, weight=1)

        ttk.Label(self.start_frame, text="Projektübersicht", font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, pady=(0, 10), sticky="w")

        project_list_frame = ttk.Frame(self.start_frame)
        project_list_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        project_list_frame.columnconfigure(0, weight=1)
        project_list_frame.rowconfigure(0, weight=1)

        cols = ("Projektname",)
        self.project_tree = ttk.Treeview(project_list_frame, columns=cols, show='headings', selectmode='browse')
        self.project_tree.heading("Projektname", text="Projektname")
        self.project_tree.column("Projektname", width=300)
        self.project_tree.grid(row=0, column=0, sticky="nsew")
        self.project_tree.bind("<Double-1>", self.on_project_double_click)

        scrollbar = ttk.Scrollbar(project_list_frame, orient=tk.VERTICAL, command=self.project_tree.yview)
        self.project_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_frame = ttk.Frame(self.start_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.btn_new_project = ttk.Button(button_frame, text="Neues Projekt erstellen", command=self.create_new_project_action)
        self.btn_new_project.pack(side=tk.LEFT, padx=5)

        self.btn_delete_project = ttk.Button(button_frame, text="Projekt löschen", command=self.delete_selected_project)
        self.btn_delete_project.pack(side=tk.LEFT, padx=5)

        # load_projects_into_list() wird jetzt in show_frame aufgerufen, wenn die Startseite angezeigt wird

    def sanitize_filename(self, name):
        # ... (Code unverändert) ...
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip()
        return name or "Unbenanntes Projekt"

    def create_new_project_action(self):
        # ... (Code unverändert bis zum Fehlerpunkt) ...
        project_name = simpledialog.askstring("Neues Projekt", "Geben Sie einen Namen für das neue Projekt ein:", parent=self.root)
        if project_name:
            sanitized_name = self.sanitize_filename(project_name)
            filename = f"{sanitized_name}.json"
            filepath = os.path.join(self.project_dir, filename)

            if os.path.exists(filepath):
                messagebox.showwarning("Konflikt", f"Ein Projekt mit dem Namen '{sanitized_name}' existiert bereits.", parent=self.root)
                return

            self.current_project_name = sanitized_name
            self.current_project_path = filepath
            self.project_data = []
            self.unsaved_changes = True # Ist neu, also "ungespeichert"
            # update_link_list KANN jetzt auf self.link_tree zugreifen, da es in __init__ erstellt wurde
            self.update_link_list()
            self.show_frame(self.project_frame) # Wechsel zur Projektansicht
            self.set_status(f"Neues Projekt '{sanitized_name}' erstellt. Bitte speichern.")


    def delete_selected_project(self):
        # ... (Code unverändert) ...
        selected_item = self.project_tree.focus()
        if not selected_item:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie zuerst ein Projekt aus der Liste aus.", parent=self.root)
            return
        project_name = self.project_tree.item(selected_item, 'values')[0]
        filepath = os.path.join(self.project_dir, f"{project_name}.json")
        if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie das Projekt '{project_name}' wirklich dauerhaft löschen?\nDiese Aktion kann nicht rückgängig gemacht werden!", parent=self.root):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    self.set_status(f"Projekt '{project_name}' gelöscht.")
                else:
                     messagebox.showwarning("Fehler", f"Projektdatei nicht gefunden: {filepath}", parent=self.root)
                self.load_projects_into_list()
            except OSError as e:
                messagebox.showerror("Fehler beim Löschen", f"Das Projekt konnte nicht gelöscht werden:\n{e}", parent=self.root)
                self.set_status(f"Fehler beim Löschen von '{project_name}'.")


    def load_projects_into_list(self):
        # ... (Code unverändert) ...
        for item in self.project_tree.get_children():
            self.project_tree.delete(item)
        try:
            files = [f for f in os.listdir(self.project_dir) if f.endswith('.json')]
            files.sort()
            for filename in files:
                project_name = os.path.splitext(filename)[0]
                self.project_tree.insert("", tk.END, values=(project_name,))
        except FileNotFoundError:
             self.set_status(f"Projektverzeichnis nicht gefunden: {self.project_dir}")
             # Keine MessageBox hier, Status reicht evtl.
        except Exception as e:
            self.set_status(f"Fehler beim Laden der Projektliste: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Lesen des Projektverzeichnisses:\n{e}", parent=self.root)


    def on_project_double_click(self, event):
        # ... (Code unverändert) ...
        selected_item = self.project_tree.focus()
        if not selected_item:
            return
        project_name = self.project_tree.item(selected_item, 'values')[0]
        filepath = os.path.join(self.project_dir, f"{project_name}.json")
        self.load_project(filepath)


    # --- Projekt-Detailseite Widgets ---
    # Umbenannt von create_project_page zu create_project_page_widgets
    def create_project_page_widgets(self):
        self.project_frame.columnconfigure(0, weight=1)
        self.project_frame.rowconfigure(1, weight=1)

        top_frame = ttk.Frame(self.project_frame)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.btn_back = ttk.Button(top_frame, text="< Zurück zur Übersicht", command=self.go_back_to_start)
        self.btn_back.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_project_title = ttk.Label(top_frame, text="Projekt: -", font=('Segoe UI', 12, 'bold'), anchor="w")
        self.lbl_project_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        link_list_frame = ttk.Frame(self.project_frame)
        link_list_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        link_list_frame.columnconfigure(0, weight=1)
        link_list_frame.rowconfigure(0, weight=1)

        link_cols = ("Beschreibung", "URL")
        # Hier wird self.link_tree jetzt sicher in __init__ initialisiert
        self.link_tree = ttk.Treeview(link_list_frame, columns=link_cols, show='headings', selectmode='browse')
        self.link_tree.heading("Beschreibung", text="Beschreibung")
        self.link_tree.heading("URL", text="URL")
        self.link_tree.column("Beschreibung", width=250, anchor="w")
        self.link_tree.column("URL", width=350, anchor="w")
        self.link_tree.grid(row=0, column=0, sticky="nsew")
        self.link_tree.bind("<Double-1>", self.open_selected_link_action)

        link_scrollbar = ttk.Scrollbar(link_list_frame, orient=tk.VERTICAL, command=self.link_tree.yview)
        self.link_tree.configure(yscrollcommand=link_scrollbar.set)
        link_scrollbar.grid(row=0, column=1, sticky="ns")

        link_button_frame = ttk.Frame(self.project_frame)
        link_button_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.btn_add_link = ttk.Button(link_button_frame, text="Link hinzufügen...", command=self.add_link_action)
        self.btn_add_link.pack(side=tk.LEFT, padx=5)

        self.btn_edit_link = ttk.Button(link_button_frame, text="Link bearbeiten...", command=self.edit_link_action)
        self.btn_edit_link.pack(side=tk.LEFT, padx=5)

        self.btn_open_link = ttk.Button(link_button_frame, text="Link öffnen", command=self.open_selected_link_action)
        self.btn_open_link.pack(side=tk.LEFT, padx=5)

        self.btn_delete_link = ttk.Button(link_button_frame, text="Link löschen", command=self.delete_selected_link_action)
        self.btn_delete_link.pack(side=tk.LEFT, padx=5)

        self.btn_save_project = ttk.Button(link_button_frame, text="Projekt speichern", command=self.save_project)
        self.btn_save_project.pack(side=tk.RIGHT, padx=5)

        # Statusleiste wurde nach __init__ verschoben
        # Der redundante self.create_project_page() Aufruf wurde entfernt

    def update_project_frame_title(self):
        # ... (Code unverändert) ...
        title = "Projekt: "
        if self.current_project_name:
            title += self.current_project_name
        else:
            title += "(Neues Projekt)"
        if self.unsaved_changes:
            title += " *"
        self.lbl_project_title.config(text=title)
        window_title = f"Link Manager - {self.current_project_name or 'Neues Projekt'}"
        if self.unsaved_changes:
            window_title += " *"
        self.root.title(window_title)


    def go_back_to_start(self):
        # ... (Code unverändert) ...
        if not self.check_unsaved_changes():
            return
        self.current_project_path = None
        self.current_project_name = None
        self.project_data = []
        self.unsaved_changes = False
        self.show_frame(self.start_frame)
        self.set_status("Projektübersicht angezeigt.")


    def update_link_list(self):
        # ... (Code unverändert, sollte jetzt funktionieren) ...
        for item in self.link_tree.get_children():
            self.link_tree.delete(item)
        for i, link in enumerate(self.project_data):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.link_tree.insert("", tk.END, text=str(i), # text als iid verwenden
                                  values=(link.get('desc', ''), link.get('url', '')),
                                  tags=(tag,))
        self.link_tree.tag_configure('evenrow', background='#f0f0f0')
        self.link_tree.tag_configure('oddrow', background='#ffffff')

    # --- Aktionen für Links ---
    def add_link_action(self):
        # ... (Code unverändert) ...
        dialog = LinkEntryDialog(self.root, title="Neuen Link hinzufügen")
        if dialog.result:
            self.project_data.append(dialog.result)
            self.update_link_list()
            self.mark_unsaved(True)
            self.set_status(f"Link '{dialog.result['desc']}' hinzugefügt.")

    def edit_link_action(self):
        # ... (Code unverändert) ...
        selected_item_id = self.link_tree.focus()
        if not selected_item_id:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie zuerst einen Link aus der Liste aus.", parent=self.root)
            return
        try:
            all_items = self.link_tree.get_children('')
            index = all_items.index(selected_item_id)
            if 0 <= index < len(self.project_data):
                original_data = self.project_data[index]
                dialog = LinkEntryDialog(self.root, title="Link bearbeiten", initial_data=original_data)
                if dialog.result:
                    self.project_data[index] = dialog.result
                    self.update_link_list()
                    self.mark_unsaved(True)
                    self.set_status(f"Link '{dialog.result['desc']}' bearbeitet.")
                    self.link_tree.focus(selected_item_id)
                    self.link_tree.selection_set(selected_item_id)
            else:
                 messagebox.showerror("Fehler", "Konnte den ausgewählten Link nicht in den Daten finden.", parent=self.root)
        except ValueError:
            messagebox.showerror("Fehler", "Konnte den Index des ausgewählten Links nicht bestimmen.", parent=self.root)
        except Exception as e:
             messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}", parent=self.root)


    def get_selected_link_data(self):
        # ... (Code unverändert) ...
        selected_item_id = self.link_tree.focus()
        if not selected_item_id:
            # Keine MessageBox hier, da es oft intern genutzt wird. Rückgabe reicht.
            # messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie zuerst einen Link aus der Liste aus.", parent=self.root)
            return None, -1
        try:
            all_items = self.link_tree.get_children('')
            index = all_items.index(selected_item_id)
            if 0 <= index < len(self.project_data):
                return self.project_data[index], index
            else:
                # Loggen wäre hier besser als MessageBox
                print(f"Error: Selected item {selected_item_id} index {index} out of bounds for project_data (len {len(self.project_data)})")
                messagebox.showerror("Fehler", "Ausgewählter Link nicht in Daten gefunden (Index inkonsistent?).", parent=self.root)
                return None, -1
        except ValueError:
             # Loggen wäre hier besser als MessageBox
             print(f"Error: Could not find index for selected item {selected_item_id} in link_tree children.")
             messagebox.showerror("Fehler", "Konnte Index des Links nicht bestimmen.", parent=self.root)
             return None, -1

    def open_selected_link_action(self, event=None):
        # ... (Code unverändert) ...
        link_data, _ = self.get_selected_link_data()
        if link_data:
            url_to_open = link_data.get('url')
            if url_to_open:
                try:
                    self.set_status(f"Öffne: {url_to_open}")
                    webbrowser.open(url_to_open)
                except Exception as e:
                    messagebox.showerror("Fehler beim Öffnen", f"Der Link konnte nicht geöffnet werden:\n{e}", parent=self.root)
                    self.set_status(f"Fehler beim Öffnen: {e}")
            else:
                messagebox.showwarning("Fehlende URL", "Für diesen Eintrag ist keine URL gespeichert.", parent=self.root)
                self.set_status("Öffnen fehlgeschlagen: URL fehlt.")

    def delete_selected_link_action(self):
        # ... (Code unverändert) ...
         link_data, index = self.get_selected_link_data()
         if link_data and index != -1: # Stelle sicher, dass der Index gültig ist
            desc = link_data.get('desc', 'diesen Link')
            url = link_data.get('url', '')
            if messagebox.askyesno("Löschen bestätigen", f"Möchten Sie den Link\n'{desc}'\n({url})\nwirklich löschen?", parent=self.root):
                try:
                    del self.project_data[index]
                    self.update_link_list()
                    self.mark_unsaved(True)
                    self.set_status(f"Link '{desc}' gelöscht.")
                except IndexError:
                    # Sollte durch die Prüfung oben nicht mehr passieren, aber sicher ist sicher
                    messagebox.showerror("Fehler", "Link konnte nicht gelöscht werden (Indexproblem).", parent=self.root)
                    self.set_status("Fehler beim Löschen: Index ungültig.")


    # --- Laden & Speichern ---
    def load_project(self, filepath):
        # ... (Code unverändert) ...
        if not self.check_unsaved_changes():
            return
        if not os.path.exists(filepath):
             messagebox.showerror("Fehler", f"Projektdatei nicht gefunden:\n{filepath}", parent=self.root)
             self.set_status("Fehler beim Laden: Datei nicht gefunden.")
             self.show_frame(self.start_frame)
             return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if not isinstance(loaded_data, list):
                    raise ValueError("Datei enthält keine gültige Link-Liste (kein JSON-Array).")
                cleaned_data = []
                for i, item in enumerate(loaded_data):
                    if isinstance(item, dict) and 'url' in item:
                        if 'desc' not in item: item['desc'] = item.get('url', 'Keine Beschreibung')
                        cleaned_data.append(item)
                    else:
                         print(f"Warnung: Ungültiges Element in {filepath} bei Index {i} übersprungen: {item}")
                self.project_data = cleaned_data
            self.current_project_path = filepath
            self.current_project_name = os.path.splitext(os.path.basename(filepath))[0]
            self.update_link_list()
            self.mark_unsaved(False)
            self.show_frame(self.project_frame)
            self.set_status(f"Projekt '{self.current_project_name}' geladen.")
        except json.JSONDecodeError:
            messagebox.showerror("Fehler", f"Ungültiges JSON-Format in Datei:\n{filepath}", parent=self.root)
            self.set_status("Fehler beim Laden: Ungültiges JSON.")
            self.show_frame(self.start_frame)
        except ValueError as e:
             messagebox.showerror("Fehler", f"Ungültiger Inhalt in Projektdatei:\n{filepath}\n{e}", parent=self.root)
             self.set_status(f"Fehler beim Laden: {e}")
             self.show_frame(self.start_frame)
        except Exception as e:
            messagebox.showerror("Fehler", f"Ein unerwarteter Fehler ist beim Laden aufgetreten:\n{e}", parent=self.root)
            self.set_status(f"Fehler beim Laden: {e}")
            self.show_frame(self.start_frame)

    def save_project(self):
        # ... (Code unverändert) ...
         if not self.current_project_path:
            if self.current_project_name:
                 filename = f"{self.current_project_name}.json"
                 self.current_project_path = os.path.join(self.project_dir, filename)
            else:
                messagebox.showerror("Fehler", "Kann Projekt nicht speichern: Kein Projektname oder Pfad bekannt.", parent=self.root)
                return False
         try:
            os.makedirs(os.path.dirname(self.current_project_path), exist_ok=True)
            with open(self.current_project_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=4, ensure_ascii=False)
            self.mark_unsaved(False)
            self.set_status(f"Projekt '{self.current_project_name}' gespeichert.")
            return True
         except Exception as e:
            messagebox.showerror("Speicherfehler", f"Projekt konnte nicht gespeichert werden:\n{self.current_project_path}\nFehler: {e}", parent=self.root)
            self.set_status(f"Fehler beim Speichern: {e}")
            return False


    def check_unsaved_changes(self):
        # ... (Code unverändert) ...
        if self.unsaved_changes:
            # Stelle sicher, dass ein Projektname existiert, sonst ist es verwirrend
            proj_display_name = self.current_project_name or "das aktuelle neue Projekt"
            response = messagebox.askyesnocancel("Ungespeicherte Änderungen",
                                                 f"Das Projekt '{proj_display_name}' hat ungespeicherte Änderungen.\nMöchten Sie sie jetzt speichern?",
                                                 parent=self.root)
            if response is True: # Ja
                return self.save_project()
            elif response is False: # Nein
                return True
            else: # Abbrechen
                return False
        return True

    def mark_unsaved(self, status=True):
        # ... (Code unverändert) ...
        self.unsaved_changes = status
        self.update_project_frame_title()

    def set_status(self, text):
        # ... (Code unverändert) ...
        self.status_var.set(text)

    def on_closing(self):
        # ... (Code unverändert) ...
         if self.project_frame.winfo_ismapped():
             if not self.check_unsaved_changes():
                 return
         self.root.destroy()

# --- Hauptprogramm ---
if __name__ == "__main__":
    # Importiere sys nur hier, wenn als Skript ausgeführt
    # (wird für den Fallback im project_dir benötigt)
    import sys
    root = tk.Tk()
    app = LinkManagerApp(root)
    root.mainloop()

# --- LinkEntryDialog Klasse ---
# (Keine Änderungen hier nötig, steht am besten am Anfang der Datei
# oder wird aus einer anderen Datei importiert)
class LinkEntryDialog(simpledialog.Dialog):
    """Ein Dialog zum Hinzufügen oder Bearbeiten eines Links."""
    def __init__(self, parent, title="Link hinzufügen/bearbeiten", initial_data=None):
        self.initial_data = initial_data or {'url': '', 'desc': ''}
        self.result = None
        super().__init__(parent, title=title)

    def body(self, master):
        ttk.Label(master, text="URL:", anchor="w").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.url_entry.insert(0, self.initial_data.get('url', ''))

        ttk.Label(master, text="Beschreibung:", anchor="w").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.desc_entry = ttk.Entry(master, width=50)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.desc_entry.insert(0, self.initial_data.get('desc', ''))

        master.columnconfigure(1, weight=1)
        return self.url_entry

    def apply(self):
        url = self.url_entry.get().strip()
        desc = self.desc_entry.get().strip()

        if not url:
            messagebox.showwarning("Eingabe fehlt", "Die URL darf nicht leer sein.", parent=self)
            self.url_entry.focus_set() # Fokus zurück auf URL-Feld
            return # Dialog bleibt offen

        if not url.startswith(("http://", "https://", "ftp://", "file://")):
             # Nur fragen, wenn es nicht schon ein bekanntes Protokoll ist
             if not re.match(r"^[a-zA-Z]+://", url): # Prüft ob *irgendein* Protokoll da ist
                 if messagebox.askyesno("URL-Format", f"Die URL '{url}' scheint kein Protokoll (z.B. http://) zu haben.\nSoll 'http://' vorangestellt werden?", parent=self):
                     url = "http://" + url

        if not desc:
            desc = url

        self.result = {'url': url, 'desc': desc}