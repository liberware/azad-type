"""A local writing desk and explicit, opt-in Windows integration."""
from dataclasses import replace
import queue
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .dictionary import Dictionary
from .engine import Engine, Settings
from .storage import data_directory, load_settings, save_settings


BG = "#101c29"
PANEL = "#172737"
TEXT = "#e8f0f5"
MUTED = "#9eafbd"
TEAL = "#65debc"


class Application:
    def __init__(self, root, profile=None):
        self.root = root
        self.profile = profile or data_directory()
        self.config_path = self.profile / "settings.json"
        self.events = queue.Queue()
        self.service = None
        self.config = load_settings(self.config_path)
        self.dictionary = Dictionary(self.profile / "dictionary.json")
        self.engine = Engine(self.dictionary, Settings(
            persian_digits=self.config.get("persian_digits", False),
            persian_punctuation=self.config.get("persian_punctuation", False)))
        root.title("Azad Type · آزاد تایپ")
        root.geometry("1060x760")
        root.minsize(850, 650)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 28, "bold"))
        style.configure("TButton", background=PANEL, foreground=TEXT, padding=(16, 9), borderwidth=0)
        style.map("TButton", background=[("active", "#284b5b")])
        style.configure("Accent.TButton", background=TEAL, foreground=BG)
        style.map("Accent.TButton", background=[("active", "#93efd3")])
        style.configure("TCheckbutton", background=BG, foreground=TEXT, padding=5)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(18, 12))
        style.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", TEAL)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=29, borderwidth=0)
        style.configure("Treeview.Heading", background=BG, foreground=TEXT)
        shell = ttk.Frame(root, padding=28)
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 24))
        ttk.Label(header, text="آزاد  /  AZAD TYPE", foreground=TEAL,
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(header, text="OFFLINE  ·  OPEN SOURCE  ·  YOUR WORDS STAY HERE",
                  style="Muted.TLabel").pack(side="right")
        ttk.Label(shell, text="Two languages. One flow.", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="فارسی و انگلیسی، کنار هم  ·  A Persian typing utility",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 22))
        notebook = ttk.Notebook(shell)
        notebook.pack(fill="both", expand=True)
        desk = ttk.Frame(notebook, padding=(0, 20))
        words = ttk.Frame(notebook, padding=(0, 20))
        desktop = ttk.Frame(notebook, padding=(0, 20))
        about = ttk.Frame(notebook, padding=(0, 20))
        for frame, title in ((desk, "Writing desk"), (words, "Dictionary"),
                             (desktop, "Windows integration"), (about, "About & privacy")):
            notebook.add(frame, text=title)
        self._desk(desk)
        self._words(words)
        self._desktop(desktop)
        self._about(about)
        self.status = tk.StringVar(value="Ready · Desktop interception is off")
        ttk.Label(shell, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(12, 0))
        self._poll = root.after(100, self._drain)

    def _text(self, parent, height=7):
        widget = tk.Text(parent, height=height, wrap="word", undo=True, maxundo=100,
                         bg=PANEL, fg=TEXT, insertbackground=TEAL, selectbackground="#34645e",
                         relief="flat", padx=20, pady=18, font=("Segoe UI", 17))
        return widget

    def _desk(self, frame):
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="WRITE HERE", foreground=TEAL).pack(side="left")
        self.live = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Convert known words on Space", variable=self.live).pack(side="right")
        self.editor = self._text(frame, 6)
        self.editor.pack(fill="both", expand=True)
        self.editor.insert("1.0", "sghl GitHub\n")
        self.editor.edit_reset()
        self.editor.bind("<KeyPress-space>", self._space)
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(12, 12))
        ttk.Button(actions, text="Smart convert", style="Accent.TButton", command=self.smart_convert).pack(side="left")
        ttk.Button(actions, text="Map selection / all", command=self.manual_convert).pack(side="left", padx=8)
        ttk.Button(actions, text="Undo", command=self.undo).pack(side="left")
        ttk.Button(actions, text="Copy", command=self.copy).pack(side="right")
        self.digits = tk.BooleanVar(value=self.engine.settings.persian_digits)
        self.punctuation = tk.BooleanVar(value=self.engine.settings.persian_punctuation)
        options = ttk.Frame(frame)
        options.pack(fill="x")
        ttk.Checkbutton(options, text="Persian digits", variable=self.digits, command=self._options).pack(side="left")
        ttk.Checkbutton(options, text="Persian punctuation", variable=self.punctuation, command=self._options).pack(side="left", padx=12)
        self.explanation = tk.StringVar(value="Try sghl → سلام. English names and technical tokens are preserved.")
        ttk.Label(frame, textvariable=self.explanation, style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(10, 0))
        ttk.Label(frame, text="Smart mode uses a small original vocabulary. Add words in Dictionary to expand it.\n"
                  "Manual mapping converts every layout character in the selected text; review its result.",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

    def _range(self):
        try:
            return self.editor.index("sel.first"), self.editor.index("sel.last")
        except tk.TclError:
            return "1.0", "end-1c"

    def _replace(self, first, last, text):
        self.editor.edit_separator()
        self.editor.configure(autoseparators=False)
        try:
            self.editor.delete(first, last)
            self.editor.insert(first, text)
        finally:
            self.editor.configure(autoseparators=True)
        self.editor.edit_separator()

    def smart_convert(self):
        first, last = self._range()
        text = self.editor.get(first, last)
        self._replace(first, last, self.engine.convert_text(text))
        self.explanation.set("Converted words with positive dictionary evidence; unknown and protected tokens kept.")

    def manual_convert(self):
        first, last = self._range()
        self._replace(first, last, self.engine.manual_convert(self.editor.get(first, last)))
        self.explanation.set("Manual physical-key mapping applied. Undo restores the original text.")

    def _space(self, event):
        if not self.live.get() or event.state & 0xC or self.editor.tag_ranges("sel"):
            return None
        prefix = self.editor.get("insert linestart", "insert")
        match = re.search(r"\S+$", prefix)
        if match:
            decision = self.engine.decide(match.group())
            self.explanation.set(decision.reason)
            if decision.converted:
                start = self.editor.index(f"insert-{len(match.group())}c")
                self._replace(start, "insert", decision.output)
        return None

    def undo(self):
        try:
            self.editor.edit_undo()
        except tk.TclError:
            pass

    def copy(self):
        first, last = self._range()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.editor.get(first, last))
        self.status.set("Copied to the local clipboard")

    def _options(self):
        self.engine.settings = replace(self.engine.settings, persian_digits=self.digits.get(),
                                       persian_punctuation=self.punctuation.get())
        self.config.update(persian_digits=self.digits.get(), persian_punctuation=self.punctuation.get())
        self._save()

    def _words(self, frame):
        ttk.Label(frame, text="Your vocabulary, on this device", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Add Persian words to recognize them, or English terms to protect them.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 14))
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 12))
        self.word = ttk.Entry(row, font=("Segoe UI", 13))
        self.word.pack(side="left", fill="x", expand=True)
        self.language = ttk.Combobox(row, values=("fa", "en"), state="readonly", width=5)
        self.language.set("fa")
        self.language.pack(side="left", padx=8)
        ttk.Button(row, text="Add word", command=self.add_word).pack(side="left")
        self.word.bind("<Return>", lambda _: self.add_word())
        self.search = tk.StringVar()
        ttk.Entry(frame, textvariable=self.search).pack(fill="x", pady=(0, 8))
        self.search.trace_add("write", lambda *_: self.refresh_words())
        self.table = ttk.Treeview(frame, columns=("word", "language"), show="headings", height=8)
        self.table.heading("word", text="Word · واژه")
        self.table.heading("language", text="Language / protection")
        self.table.pack(fill="both", expand=True)
        tools = ttk.Frame(frame)
        tools.pack(fill="x", pady=(12, 0))
        ttk.Button(tools, text="Import JSON / CSV / TXT", command=self.import_words).pack(side="left")
        ttk.Button(tools, text="Export vocabulary", command=self.export_words).pack(side="left", padx=8)
        ttk.Button(tools, text="Remove personal entry", command=self.remove_word).pack(side="right")
        self.refresh_words()

    def refresh_words(self):
        self.table.delete(*self.table.get_children())
        query = self.search.get().casefold()
        entries = [(word, "fa · Persian") for word in self.dictionary.persian_words]
        entries += [(word, "en · protected") for word in self.dictionary.protected_words]
        for word, language in sorted(entries):
            if query in word.casefold():
                self.table.insert("", "end", values=(word, language))

    def add_word(self, text=None):
        try:
            language = ("fa" if re.search(r"[\u0600-\u06ff]", text) else "en") if text is not None else self.language.get()
            self.dictionary.add(text if text is not None else self.word.get(), language)
            self.word.delete(0, "end")
            self.refresh_words()
            self.status.set("Vocabulary saved locally")
        except (ValueError, OSError) as error:
            messagebox.showerror("Dictionary", str(error), parent=self.root)

    def remove_word(self):
        try:
            for item in self.table.selection():
                word, language = self.table.item(item, "values")
                self.dictionary.remove(word, language[:2])
            self.refresh_words()
            self.status.set("Personal entries removed; built-in vocabulary stays available")
        except (ValueError, OSError) as error:
            messagebox.showerror("Dictionary", str(error), parent=self.root)

    def import_words(self):
        path = filedialog.askopenfilename(filetypes=[("Vocabulary", "*.json *.csv *.txt")])
        if path:
            try:
                self.dictionary.import_file(path)
                self.refresh_words()
                self.status.set("Vocabulary imported")
            except (ValueError, OSError) as error:
                messagebox.showerror("Import", str(error), parent=self.root)

    def export_words(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("CSV", "*.csv"), ("Text", "*.txt")])
        if path:
            try:
                self.dictionary.export_file(path)
                self.status.set("Vocabulary exported")
            except (ValueError, OSError) as error:
                messagebox.showerror("Export", str(error), parent=self.root)

    def _desktop(self, frame):
        ttk.Label(frame, text="Enable only where you choose", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Global typing starts only when you enable it below, and stops when this app closes.\n"
                  "Only verified, writable classic Windows Edit / RichEdit fields are eligible. Browser, modern\n"
                  "Notepad and other unknown fields are skipped. No administrator rights are requested.",
                  style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(12, 18))
        ttk.Label(frame, text="Allowed application executable names, separated by commas").pack(anchor="w")
        self.allowed = ttk.Entry(frame)
        self.allowed.insert(0, ", ".join(self.config.get("allowed_apps", [])))
        self.allowed.pack(fill="x", pady=(8, 15))
        ttk.Label(frame, text="Example: wordpad.exe. A name alone does not bypass the field checks.",
                  style="Muted.TLabel").pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=20)
        self.enable_button = ttk.Button(buttons, text="Enable desktop typing", command=self.toggle_desktop,
                                        style="Accent.TButton")
        self.enable_button.pack(side="left")
        self.pause_button = ttk.Button(buttons, text="Pause / resume", command=self.pause)
        self.pause_button.pack(side="left", padx=10)
        ttk.Label(frame, text="Ctrl + Alt + Space    Convert the tracked previous word\n"
                  "Ctrl + Alt + Enter     Map selected text\n"
                  "Ctrl + Alt + U            Undo the last manual conversion\n"
                  "Ctrl + Alt + D            Add selected text to the dictionary\n"
                  "Ctrl + Alt + P            Pause / resume\n"
                  "Backspace                 Undo the last automatic conversion",
                  foreground=TEXT, font=("Segoe UI", 12), justify="left").pack(anchor="w", pady=8)
        ttk.Label(frame, text="Selection commands operate only in verified classic text controls. Typed words\n"
                  "are kept only in temporary memory; no keystroke logs are written.",
                  style="Muted.TLabel").pack(anchor="w", pady=16)

    def toggle_desktop(self):
        if self.service:
            self.service.stop()
            self.service = None
            self.enable_button.configure(text="Enable desktop typing")
            self.status.set("Desktop interception is off")
            return
        if sys.platform != "win32":
            messagebox.showinfo("Windows integration", "The writing desk works here; global typing requires Windows.")
            return
        apps = sorted(set(s.strip().lower() for s in self.allowed.get().split(",") if s.strip()))
        if not apps or any(not re.fullmatch(r"[\w .-]+\.exe", a) for a in apps):
            messagebox.showerror("Allowed applications", "Enter at least one executable basename, such as wordpad.exe.")
            return
        try:
            from .windows import WindowsTypingService
            def decide(word):
                decision = self.engine.decide(word)
                return decision.output if decision.converted else None
            self.service = WindowsTypingService(decide=decide,
                transform_selection=self.engine.manual_convert,
                add_word=lambda text: self.events.put(("word", text)),
                on_status=lambda status: self.events.put(("status", status)), allowed_apps=apps)
            self.service.start()
            self.config["allowed_apps"] = apps
            self._save()
            self.enable_button.configure(text="Disable desktop typing")
            self.status.set("Desktop typing enabled for verified fields in your allowed applications")
        except (OSError, RuntimeError, ValueError) as error:
            if self.service:
                self.service.stop()
                self.service = None
            messagebox.showerror("Windows integration", str(error), parent=self.root)

    def pause(self):
        if self.service:
            self.service.set_paused(not self.service.paused)

    def _about(self, frame):
        ttk.Label(frame, text=f"Azad Type {__version__}", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        text = ("Persian/English keyboard-layout conversion.\n\n"
                "Python code and a small vocabulary, released under the MIT license.\n\n"
                "Everything in this implementation works offline. There is no network client, telemetry,\n"
                "cloud translation, update downloader or background service. Settings and your vocabulary\n"
                "are saved locally. Writing-desk text is never saved automatically.\n\n"
                "This is an early implementation with limited editor compatibility, not feature parity.\n"
                "TSF, UI Automation for modern fields, system tray, language-switch key modes,\n"
                "translation and external-app font management are not implemented.\n\n"
                "Keep the keyboard on English (US). Smart conversion requires a known Persian word;\n"
                "unknown words stay as typed. Use manual mapping or add vocabulary when needed.\n\n"
                f"Local profile: {self.profile}")
        ttk.Label(frame, text=text, justify="left", wraplength=900, style="Muted.TLabel").pack(anchor="w", pady=18)

    def _save(self):
        try:
            save_settings(self.config_path, self.config)
        except OSError as error:
            messagebox.showerror("Settings", str(error), parent=self.root)

    def _drain(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "word":
                    self.add_word(value)
                else:
                    self.status.set(str(value))
        except queue.Empty:
            pass
        self._poll = self.root.after(100, self._drain)

    def close(self):
        if self.service:
            self.service.stop()
        self.root.after_cancel(self._poll)
        self.root.destroy()


def launch():
    root = tk.Tk()
    try:
        Application(root)
    except (ValueError, OSError) as error:
        messagebox.showerror("Azad Type", f"Could not read the local profile: {error}", parent=root)
        root.destroy()
        return
    root.mainloop()
