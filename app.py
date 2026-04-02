"""
CallGiant - Tkinter GUI Application
Five-tab interface: Leads, Message, Settings, Call Control, Call Logs.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
import re
import queue as q
import threading

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

import database as db
from caller import CallEngine


class CallGiantApp:
    # ── Premium Dark Palette ──
    BG          = "#0f1923"       # deep navy
    BG_CARD     = "#162333"       # card surfaces
    BG_LIGHT    = "#1e3044"       # lighter panels / hover
    BG_INPUT    = "#0c1219"       # input fields
    FG          = "#e8edf2"       # primary text
    FG_DIM      = "#7a8fa6"       # secondary text
    FG_MUTED    = "#4a5d73"       # muted hints
    ACCENT      = "#00b4d8"       # electric cyan
    ACCENT_DIM  = "#0090b0"       # subtle accent
    GOLD        = "#f0c040"       # highlight / brand
    GREEN       = "#00c853"       # go / success
    GREEN_HOVER = "#00e676"
    RED         = "#ff1744"       # stop / danger
    RED_HOVER   = "#ff5252"
    ENTRY_BG    = "#0c1219"
    ENTRY_FG    = "#e8edf2"
    BORDER      = "#1e3044"

    VERSION = "1.0.0"

    def __init__(self, root):
        self.root = root
        self.root.title("CallGiant")
        self.root.geometry("1200x850")
        self.root.minsize(960, 640)
        self.root.configure(bg=self.BG)

        db.init_db()
        self.engine = CallEngine()

        self._apply_dark_theme()

        # ── Branded Header ──
        header = tk.Frame(root, bg=self.BG, height=68)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(header, bg=self.BG)
        logo_frame.pack(side=tk.LEFT, padx=20, pady=10)

        tk.Label(
            logo_frame, text="📞", font=("Segoe UI Emoji", 24),
            bg=self.BG, fg=self.ACCENT,
        ).pack(side=tk.LEFT, padx=(0, 10))

        title_frame = tk.Frame(logo_frame, bg=self.BG)
        title_frame.pack(side=tk.LEFT)
        tk.Label(
            title_frame, text="CallGiant",
            font=("Segoe UI", 22, "bold"), bg=self.BG, fg=self.FG,
        ).pack(anchor=tk.W)
        tk.Label(
            title_frame, text="Automated Calling System",
            font=("Segoe UI", 9), bg=self.BG, fg=self.FG_DIM,
        ).pack(anchor=tk.W)

        # Version badge
        tk.Label(
            header, text=f"v{self.VERSION}",
            font=("Segoe UI", 8), bg=self.BG_CARD, fg=self.FG_DIM,
            padx=8, pady=2,
        ).pack(side=tk.RIGHT, padx=20, pady=20)

        # ── Separator line ──
        sep = tk.Frame(root, bg=self.ACCENT, height=2)
        sep.pack(fill=tk.X)

        # ── Main container ──
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ── Notebook ──
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_leads_tab()
        self._build_message_tab()
        self._build_settings_tab()
        self._build_control_tab()
        self._build_logs_tab()

        # ── Status bar ──
        status_sep = tk.Frame(root, bg=self.BORDER, height=1)
        status_sep.pack(fill=tk.X)

        status_bar = tk.Frame(root, bg="#080e14", height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Ready")
        # Dot indicator
        self.status_dot = tk.Label(
            status_bar, text="●", font=("Segoe UI", 8),
            bg="#080e14", fg=self.GREEN,
        )
        self.status_dot.pack(side=tk.LEFT, padx=(12, 4))

        tk.Label(
            status_bar, textvariable=self.status_var,
            bg="#080e14", fg=self.FG_DIM,
            font=("Segoe UI", 9), anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            status_bar, text="CallGiant",
            bg="#080e14", fg=self.FG_MUTED,
            font=("Segoe UI", 8), padx=12,
        ).pack(side=tk.RIGHT)

        self._load_settings()
        self._setup_auto_save()
        self._refresh_leads_table()
        self._refresh_logs_table()
        self._poll_engine()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────
    #  Premium Dark Theme
    # ─────────────────────────────────────────────
    def _apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Global defaults
        style.configure(".",
            background=self.BG, foreground=self.FG,
            fieldbackground=self.BG_INPUT, borderwidth=0,
            font=("Segoe UI", 10))

        # Frames
        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.BG_CARD)

        # LabelFrames (card-style groups)
        style.configure("TLabelframe", background=self.BG_CARD,
                        foreground=self.FG, relief="flat", borderwidth=1)
        style.configure("TLabelframe.Label", background=self.BG_CARD,
                        foreground=self.ACCENT, font=("Segoe UI", 11, "bold"))

        # Notebook (tabs)
        style.configure("TNotebook", background=self.BG, borderwidth=0, padding=0)
        style.configure("TNotebook.Tab",
            background=self.BG_CARD, foreground=self.FG_DIM,
            padding=[20, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
            background=[("selected", self.BG_LIGHT), ("active", self.BG_LIGHT)],
            foreground=[("selected", self.ACCENT), ("active", self.FG)])

        # Labels
        style.configure("TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=self.BG_CARD, foreground=self.FG,
                        font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 14, "bold"))
        style.configure("CardHeader.TLabel", background=self.BG_CARD,
                        foreground=self.ACCENT, font=("Segoe UI", 11, "bold"))
        style.configure("Dim.TLabel", background=self.BG_CARD, foreground=self.FG_DIM,
                        font=("Segoe UI", 9))
        style.configure("Stat.TLabel", background=self.BG_CARD, foreground=self.GOLD,
                        font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TLabel", background=self.BG, foreground=self.ACCENT,
                        font=("Segoe UI", 10, "bold"))

        # Buttons — primary
        style.configure("TButton",
            background=self.ACCENT, foreground="#ffffff",
            font=("Segoe UI", 10, "bold"), padding=[14, 6],
            borderwidth=0)
        style.map("TButton",
            background=[("active", self.ACCENT_DIM), ("disabled", self.BG_LIGHT)],
            foreground=[("disabled", self.FG_MUTED)])

        # Danger button
        style.configure("Danger.TButton",
            background="#cc1133", foreground="#ffffff",
            font=("Segoe UI", 10, "bold"), padding=[14, 6])
        style.map("Danger.TButton",
            background=[("active", self.RED), ("disabled", self.BG_LIGHT)])

        # Entry
        style.configure("TEntry",
            fieldbackground=self.BG_INPUT, foreground=self.ENTRY_FG,
            insertcolor=self.ACCENT, borderwidth=1, padding=[6, 5],
            relief="flat")

        # Treeview
        style.configure("Treeview",
            background=self.BG_INPUT, foreground=self.FG,
            fieldbackground=self.BG_INPUT, borderwidth=0,
            font=("Segoe UI", 10), rowheight=30)
        style.configure("Treeview.Heading",
            background=self.BG_CARD, foreground=self.ACCENT,
            font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat",
            padding=[0, 6])
        style.map("Treeview",
            background=[("selected", self.ACCENT_DIM)],
            foreground=[("selected", "#ffffff")])

        # Scrollbar
        style.configure("Vertical.TScrollbar",
            background=self.BG_CARD, troughcolor=self.BG_INPUT,
            arrowcolor=self.FG_DIM, borderwidth=0, width=10)
        style.configure("Horizontal.TScrollbar",
            background=self.BG_CARD, troughcolor=self.BG_INPUT,
            arrowcolor=self.FG_DIM, borderwidth=0)

        # Progressbar — cyan glow
        style.configure("Cyan.Horizontal.TProgressbar",
            background=self.ACCENT, troughcolor=self.BG_INPUT,
            borderwidth=0, thickness=8)
        # Green progress
        style.configure("Green.Horizontal.TProgressbar",
            background=self.GREEN, troughcolor=self.BG_INPUT,
            borderwidth=0, thickness=8)

        # Checkbutton / Radiobutton
        style.configure("TCheckbutton", background=self.BG, foreground=self.FG)
        style.configure("TRadiobutton", background=self.BG, foreground=self.FG)

        # Separator
        style.configure("TSeparator", background=self.BORDER)

    # ═══════════════════════════════════════════
    #  TAB 1 — Leads Import
    # ═══════════════════════════════════════════
    def _build_leads_tab(self):
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="  📋  Leads  ")

        # Top bar
        bar = ttk.Frame(tab)
        bar.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(bar, text="⬆  Import CSV / XLSX",
                   command=self._import_leads).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(bar, text="🗑  Clear All", style="Danger.TButton",
                   command=self._clear_leads).pack(side=tk.LEFT)

        self.leads_count_var = tk.StringVar(value="0 leads loaded")
        ttk.Label(bar, textvariable=self.leads_count_var,
                  style="Accent.TLabel").pack(side=tk.RIGHT)

        # Table with scrollbars in a card background
        tree_card = tk.Frame(tab, bg=self.BG_INPUT, bd=0, highlightthickness=1,
                             highlightbackground=self.BORDER)
        tree_card.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "phone", "name", "company")
        self.leads_tree = ttk.Treeview(tree_card, columns=cols, show="headings", height=20)
        for cid, text, width in [
            ("id", "#", 50), ("phone", "Phone Number", 200),
            ("name", "Lead Name", 260), ("company", "Company", 260),
        ]:
            self.leads_tree.heading(cid, text=text)
            self.leads_tree.column(cid, width=width, minwidth=40)

        vsb = ttk.Scrollbar(tree_card, orient=tk.VERTICAL, command=self.leads_tree.yview)
        hsb = ttk.Scrollbar(tree_card, orient=tk.HORIZONTAL, command=self.leads_tree.xview)
        self.leads_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.leads_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_card.rowconfigure(0, weight=1)
        tree_card.columnconfigure(0, weight=1)

    def _import_leads(self):
        ftypes = [("CSV files", "*.csv")]
        if XLSX_AVAILABLE:
            ftypes.insert(0, ("Excel files", "*.xlsx"))
        ftypes.append(("All files", "*.*"))

        path = filedialog.askopenfilename(title="Select Leads File", filetypes=ftypes)
        if not path:
            return
        try:
            leads = self._parse_file(path)
            if leads:
                db.add_leads(leads)
                self._refresh_leads_table()
                messagebox.showinfo("Import", f"Imported {len(leads)} leads.")
            else:
                messagebox.showwarning("Import", "No valid leads found.")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def _parse_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return self._parse_csv(path)
        elif ext == ".xlsx":
            return self._parse_xlsx(path)
        raise ValueError(f"Unsupported file type: {ext}")

    # ── Column auto-detection constants ──
    _PHONE_NAMES   = ["phone", "phone_number", "phonenumber", "number",
                      "telephone", "mobile", "cell", "cell_phone",
                      "tel", "fax", "contact_phone", "work_phone",
                      "home_phone", "mobile_phone", "primary_phone"]
    _NAME_NAMES    = ["name", "full_name", "fullname", "contact",
                      "contact_name", "first_name", "last_name",
                      "firstname", "lastname", "lead_name"]
    _COMPANY_NAMES = ["company", "company_name", "organization", "org",
                      "business", "business_name", "employer"]

    @staticmethod
    def _normalize_phone(raw: str) -> str:
        """Normalize a phone number toward E.164 format.
        Strips non-digit chars (except leading +), prepends +1 for
        10-digit US numbers.  Returns empty string if invalid."""
        raw = raw.strip()
        if not raw:
            return ""
        # Keep leading + if present
        if raw.startswith("+"):
            digits = re.sub(r"[^\d]", "", raw)
            return "+" + digits if len(digits) >= 10 else ""
        digits = re.sub(r"[^\d]", "", raw)
        if len(digits) == 10:          # US number without country code
            return "+1" + digits
        elif len(digits) == 11 and digits.startswith("1"):  # 1XXXXXXXXXX
            return "+" + digits
        elif len(digits) >= 10:         # international
            return "+" + digits
        return ""                       # too short / invalid

    def _parse_csv(self, path):
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            original_hdrs = list(reader.fieldnames or [])
            all_rows_raw = list(reader)

        if not original_hdrs:
            raise ValueError("File has no headers.")

        hdrs_lower = [h.lower().strip() for h in original_hdrs]

        phone_col   = self._find_col(hdrs_lower, self._PHONE_NAMES)
        name_col    = self._find_col(hdrs_lower, self._NAME_NAMES)
        company_col = self._find_col(hdrs_lower, self._COMPANY_NAMES)

        # If phone column not auto-detected, ask the user
        if phone_col is None:
            chosen = self._ask_user_for_column(
                original_hdrs,
                "Phone Column",
                "No phone column was auto-detected.\n"
                "Please select the column that contains phone numbers:",
            )
            if chosen is None:
                raise ValueError("Import cancelled — no phone column selected.")
            phone_col = chosen.lower().strip()

        leads = []
        skipped = 0
        for row in all_rows_raw:
            vals = {k.lower().strip(): v for k, v in row.items()}
            phone = self._normalize_phone(vals.get(phone_col, ""))
            if phone:
                leads.append({
                    "phone": phone,
                    "name": vals.get(name_col, "").strip() if name_col else "",
                    "company": vals.get(company_col, "").strip() if company_col else "",
                })
            else:
                skipped += 1
        if skipped:
            messagebox.showwarning(
                "Phone Numbers",
                f"{skipped} rows had invalid phone numbers and were skipped.\n"
                "Phone numbers must be at least 10 digits (e.g. +15551234567).")
        return leads

    def _parse_xlsx(self, path):
        if not XLSX_AVAILABLE:
            raise ValueError("openpyxl not installed. Run: pip install openpyxl")
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return []

        original_hdrs = [str(h).strip() if h else f"Column {i+1}"
                         for i, h in enumerate(rows[0])]
        hdrs_lower = [h.lower() for h in original_hdrs]

        phone_col   = self._find_col(hdrs_lower, self._PHONE_NAMES)
        name_col    = self._find_col(hdrs_lower, self._NAME_NAMES)
        company_col = self._find_col(hdrs_lower, self._COMPANY_NAMES)

        # If phone column not auto-detected, ask the user
        if phone_col is None:
            chosen = self._ask_user_for_column(
                original_hdrs,
                "Phone Column",
                "No phone column was auto-detected.\n"
                "Please select the column that contains phone numbers:",
            )
            if chosen is None:
                raise ValueError("Import cancelled — no phone column selected.")
            phone_col = chosen.lower().strip()

        pi = hdrs_lower.index(phone_col)
        ni = hdrs_lower.index(name_col) if name_col else None
        ci = hdrs_lower.index(company_col) if company_col else None

        leads = []
        skipped = 0
        for row in rows[1:]:
            if pi >= len(row):
                continue
            raw = row[pi]
            # Handle numeric phone values (Excel may store as float)
            if isinstance(raw, (int, float)):
                phone_raw = str(int(raw))
            else:
                phone_raw = str(raw or "").strip()
            phone = self._normalize_phone(phone_raw)
            if phone:
                leads.append({
                    "phone": phone,
                    "name": str(row[ni] or "").strip() if ni is not None and ni < len(row) else "",
                    "company": str(row[ci] or "").strip() if ci is not None and ci < len(row) else "",
                })
            else:
                skipped += 1
        if skipped:
            messagebox.showwarning(
                "Phone Numbers",
                f"{skipped} rows had invalid phone numbers and were skipped.\n"
                "Phone numbers must be at least 10 digits (e.g. +15551234567).")
        return leads

    @staticmethod
    def _find_col(headers, candidates):
        """Case-insensitive match: exact first, then substring / contains."""
        # Pass 1 — exact match
        for c in candidates:
            for h in headers:
                if h == c:
                    return h
        # Pass 2 — header contains a candidate as a substring
        for c in candidates:
            for h in headers:
                if c in h:
                    return h
        # Pass 3 — candidate contained within header (broader)
        for h in headers:
            for c in candidates:
                if h in c:
                    return h
        return None

    def _ask_user_for_column(self, columns, title, prompt_text):
        """
        Show a modal dialog listing all column names from the file.
        Returns the selected column name, or None if cancelled.
        """
        result = [None]

        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("420x400")
        dlg.resizable(False, True)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(bg=self.BG)

        ttk.Label(dlg, text=prompt_text, wraplength=380,
                  justify=tk.LEFT).pack(padx=14, pady=(14, 8), anchor=tk.W)

        # Listbox with scrollbar
        lb_frame = ttk.Frame(dlg)
        lb_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        lb_sb = ttk.Scrollbar(lb_frame, orient=tk.VERTICAL)
        listbox = tk.Listbox(
            lb_frame, font=("Segoe UI", 11), selectmode=tk.SINGLE,
            yscrollcommand=lb_sb.set, activestyle="dotbox",
            bg=self.BG_INPUT, fg=self.FG, selectbackground=self.ACCENT,
            selectforeground=self.FG, relief=tk.FLAT, bd=0,
        )
        lb_sb.config(command=listbox.yview)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_sb.pack(side=tk.RIGHT, fill=tk.Y)

        for col in columns:
            listbox.insert(tk.END, col)

        # Sample values hint — show first value from each column
        hint_var = tk.StringVar(value="")
        ttk.Label(dlg, textvariable=hint_var, style="Dim.TLabel",
                  wraplength=380).pack(padx=14, anchor=tk.W)

        def on_select(event=None):
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                hint_var.set(f'Selected: "{columns[idx]}"')

        listbox.bind("<<ListboxSelect>>", on_select)

        # Buttons
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=14, pady=(6, 14))

        def on_ok():
            sel = listbox.curselection()
            if sel:
                result[0] = columns[sel[0]]
                dlg.destroy()
            else:
                messagebox.showwarning("Select Column",
                                       "Please select a column.", parent=dlg)

        def on_cancel():
            dlg.destroy()

        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

        # Double-click = OK
        listbox.bind("<Double-1>", lambda e: on_ok())

        # Center dialog on parent
        dlg.update_idletasks()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        dw = dlg.winfo_width()
        dh = dlg.winfo_height()
        dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        self.root.wait_window(dlg)
        return result[0]

    def _refresh_leads_table(self):
        for item in self.leads_tree.get_children():
            self.leads_tree.delete(item)
        leads = db.get_all_leads()
        for ld in leads:
            self.leads_tree.insert("", tk.END, values=(
                ld["id"], ld["phone"], ld["name"], ld["company"],
            ))
        self.leads_count_var.set(f"📋  {len(leads)} leads loaded")

    def _clear_leads(self):
        if messagebox.askyesno("Clear Leads", "Remove all imported leads?"):
            db.clear_leads()
            self._refresh_leads_table()

    # ═══════════════════════════════════════════
    #  TAB 2 — Message
    # ═══════════════════════════════════════════
    def _build_message_tab(self):
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="  💬  Message  ")

        # Header
        hdr = ttk.Frame(tab)
        hdr.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(hdr, text="TTS Script",
                  style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(hdr, text="This message is spoken to callers when they answer.",
                  style="Dim.TLabel").pack(side=tk.LEFT, padx=(12, 0), pady=(4, 0))

        # Text editor in a card
        editor_card = tk.Frame(tab, bg=self.BG_INPUT, highlightthickness=1,
                               highlightbackground=self.BORDER, highlightcolor=self.ACCENT)
        editor_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.message_text = tk.Text(
            editor_card, wrap=tk.WORD, height=12, undo=True,
            font=("Consolas", 12), relief=tk.FLAT, bd=0,
            bg=self.BG_INPUT, fg=self.ENTRY_FG,
            insertbackground=self.ACCENT, insertwidth=2,
            selectbackground=self.ACCENT_DIM,
            selectforeground="#ffffff",
            padx=14, pady=12,
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)

        # Character count
        self.char_count_var = tk.StringVar(value="0 characters")
        def _update_char_count(*_):
            n = len(self.message_text.get("1.0", "end-1c"))
            self.char_count_var.set(f"{n} characters")
        self.message_text.bind("<KeyRelease>", _update_char_count)

        bottom = ttk.Frame(tab)
        bottom.pack(fill=tk.X)
        ttk.Button(bottom, text="🔊  Preview TTS", command=self._test_tts).pack(side=tk.LEFT)
        ttk.Button(bottom, text="💾  Save Message", command=self._save_message).pack(side=tk.LEFT, padx=10)
        ttk.Label(bottom, textvariable=self.char_count_var,
                  style="Dim.TLabel").pack(side=tk.RIGHT)

    def _test_tts(self):
        text = self.message_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("TTS", "Type a message first.")
            return
        if not TTS_AVAILABLE:
            messagebox.showerror("TTS", "pyttsx3 not installed.\nRun:  pip install pyttsx3")
            return
        def _speak():
            try:
                eng = pyttsx3.init()
                eng.say(text)
                eng.runAndWait()
                eng.stop()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("TTS Error", str(e)))
        threading.Thread(target=_speak, daemon=True).start()

    def _save_message(self):
        text = self.message_text.get("1.0", tk.END).strip()
        db.save_setting("tts_message", text)
        messagebox.showinfo("Saved", "Message saved.")

    # ═══════════════════════════════════════════
    #  TAB 3 — Call Settings
    # ═══════════════════════════════════════════
    def _build_settings_tab(self):
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="  ⚙  Settings  ")
        self.setting_vars = {}

        # Scrollable container for settings
        canvas = tk.Canvas(tab, bg=self.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── Twilio Credentials card ──
        grp1 = ttk.LabelFrame(scroll_frame, text="  🔑  Twilio Credentials  ", padding=16)
        grp1.pack(fill=tk.X, pady=(0, 12), padx=4)

        fields = [
            ("twilio_sid",    "Account SID",           "",     False),
            ("twilio_token",  "Auth Token",            "",     True),
            ("twilio_number", "Twilio Phone Number",   "+1…",  False),
        ]
        for i, (key, label, ph, secret) in enumerate(fields):
            ttk.Label(grp1, text=label, style="Card.TLabel").grid(
                row=i, column=0, sticky=tk.W, pady=6, padx=(0, 12))
            var = tk.StringVar()
            ent = ttk.Entry(grp1, textvariable=var, width=52,
                            show="●" if secret else "")
            ent.grid(row=i, column=1, sticky=tk.EW, pady=6)
            self.setting_vars[key] = var
        grp1.columnconfigure(1, weight=1)

        # ── Agent Transfer Numbers card (simultaneous ring) ──
        grp_agents = ttk.LabelFrame(scroll_frame,
                                     text="  👥  Agent Transfer Numbers  ", padding=16)
        grp_agents.pack(fill=tk.X, pady=(0, 12), padx=4)

        agent_fields = [
            ("agent_number_1", "Agent 1"),
            ("agent_number_2", "Agent 2"),
            ("agent_number_3", "Agent 3"),
        ]
        for i, (key, label) in enumerate(agent_fields):
            ttk.Label(grp_agents, text=label, style="Card.TLabel").grid(
                row=i, column=0, sticky=tk.W, pady=6, padx=(0, 12))
            var = tk.StringVar()
            ttk.Entry(grp_agents, textvariable=var, width=52).grid(
                row=i, column=1, sticky=tk.EW, pady=6)
            self.setting_vars[key] = var
        ttk.Label(grp_agents,
                  text="All filled numbers ring simultaneously — first pickup gets the call.",
                  style="Dim.TLabel").grid(row=len(agent_fields), column=0,
                                           columnspan=2, sticky=tk.W, pady=(4, 0))
        grp_agents.columnconfigure(1, weight=1)

        # ── Webhook card ──
        grp_wh = ttk.LabelFrame(scroll_frame, text="  🌐  Webhook  ", padding=16)
        grp_wh.pack(fill=tk.X, pady=(0, 12), padx=4)

        ttk.Label(grp_wh, text="Webhook URL", style="Card.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=6, padx=(0, 12))
        self.setting_vars["webhook_url"] = tk.StringVar(
            value="https://callgiant-backend.onrender.com")
        ttk.Entry(grp_wh, textvariable=self.setting_vars["webhook_url"],
                  width=52).grid(row=0, column=1, sticky=tk.EW, pady=6)
        ttk.Label(grp_wh, text="The hosted server that handles Twilio call flow "
                  "(do not change unless you self-host).",
                  style="Dim.TLabel").grid(row=1, column=1, sticky=tk.W)
        grp_wh.columnconfigure(1, weight=1)

        # ── Timing card ──
        grp2 = ttk.LabelFrame(scroll_frame, text="  ⏱  Timing  ", padding=16)
        grp2.pack(fill=tk.X, pady=(0, 12), padx=4)

        ttk.Label(grp2, text="Delay between calls (seconds)",
                  style="Card.TLabel").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.setting_vars["call_delay"] = tk.StringVar(value="5")
        ttk.Entry(grp2, textvariable=self.setting_vars["call_delay"],
                  width=10).grid(row=0, column=1, sticky=tk.W, pady=6, padx=12)

        # ── Save button ──
        save_frame = ttk.Frame(scroll_frame)
        save_frame.pack(fill=tk.X, pady=16, padx=4)
        ttk.Button(save_frame, text="💾  Save All Settings",
                   command=self._save_settings).pack(side=tk.RIGHT)

    def _load_settings(self):
        for key, var in self.setting_vars.items():
            val = db.get_setting(key, "")
            if val:
                var.set(val)

        # Backward-compat: migrate old single agent_number → agent_number_1
        old_agent = db.get_setting("agent_number", "")
        if old_agent and not db.get_setting("agent_number_1", ""):
            self.setting_vars["agent_number_1"].set(old_agent)
            db.save_setting("agent_number_1", old_agent)

        msg = db.get_setting("tts_message", "")
        if msg:
            self.message_text.delete("1.0", tk.END)
            self.message_text.insert("1.0", msg)

    def _save_settings(self):
        for key, var in self.setting_vars.items():
            db.save_setting(key, var.get())
        messagebox.showinfo("Saved", "All settings saved.")

    def _setup_auto_save(self):
        """Attach traces to all setting variables so changes save to DB instantly."""
        for key, var in self.setting_vars.items():
            var.trace_add("write", lambda *_a, k=key, v=var: db.save_setting(k, v.get()))

    # ═══════════════════════════════════════════
    #  TAB 4 — Call Control
    # ═══════════════════════════════════════════
    def _build_control_tab(self):
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="  📞  Call Control  ")

        # ── Big action buttons ──
        btn_frame = tk.Frame(tab, bg=self.BG)
        btn_frame.pack(pady=(8, 16))

        self.start_btn = tk.Button(
            btn_frame, text="▶   START CALLING",
            font=("Segoe UI", 20, "bold"),
            bg=self.GREEN, fg="white",
            activebackground=self.GREEN_HOVER, activeforeground="white",
            width=17, height=2, cursor="hand2",
            relief=tk.FLAT, bd=0, highlightthickness=0,
            command=self._start_calling,
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.pause_btn = tk.Button(
            btn_frame, text="⏸   PAUSE",
            font=("Segoe UI", 20, "bold"),
            bg="#1a2636", fg="#3a5068",
            activebackground="#e6a800", activeforeground="white",
            width=10, height=2, cursor="hand2",
            relief=tk.FLAT, bd=0, highlightthickness=0,
            state=tk.DISABLED, command=self._toggle_pause,
        )
        self.pause_btn.pack(side=tk.LEFT, padx=10)

        self.stop_btn = tk.Button(
            btn_frame, text="■   STOP",
            font=("Segoe UI", 20, "bold"),
            bg="#331111", fg="#663333",
            activebackground=self.RED, activeforeground="white",
            width=10, height=2, cursor="hand2",
            relief=tk.FLAT, bd=0, highlightthickness=0,
            state=tk.DISABLED, command=self._stop_calling,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        # ── Progress section ──
        prog_card = tk.Frame(tab, bg=self.BG_CARD, highlightthickness=1,
                             highlightbackground=self.BORDER)
        prog_card.pack(fill=tk.X, padx=4, pady=(0, 12))

        prog_inner = tk.Frame(prog_card, bg=self.BG_CARD)
        prog_inner.pack(fill=tk.X, padx=16, pady=12)

        self.progress_var = tk.StringVar(value="Ready")
        tk.Label(prog_inner, textvariable=self.progress_var,
                 font=("Segoe UI", 11, "bold"), bg=self.BG_CARD,
                 fg=self.FG).pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(
            prog_inner, mode="determinate", length=400,
            style="Cyan.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(6, 0))

        # ── Live log ──
        log_header = ttk.Frame(tab)
        log_header.pack(fill=tk.X, padx=4, pady=(0, 4))
        ttk.Label(log_header, text="Live Call Log",
                  style="Accent.TLabel").pack(side=tk.LEFT)

        log_card = tk.Frame(tab, bg=self.BG_INPUT, highlightthickness=1,
                            highlightbackground=self.BORDER)
        log_card.pack(fill=tk.BOTH, expand=True, padx=4)

        self.log_text = tk.Text(
            log_card, wrap=tk.WORD, state=tk.DISABLED,
            bg="#080e14", fg="#8ec8e8",
            insertbackground=self.ACCENT,
            selectbackground=self.ACCENT_DIM, selectforeground="#ffffff",
            font=("Cascadia Code", 10), relief=tk.FLAT, bd=0,
            padx=14, pady=10,
        )
        log_sb = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _start_calling(self):
        # Guard against double-start
        if self.engine.running:
            return

        # Persist current settings + message before starting
        for key, var in self.setting_vars.items():
            db.save_setting(key, var.get())
        db.save_setting("tts_message", self.message_text.get("1.0", tk.END).strip())

        self.start_btn.config(state=tk.DISABLED, bg=self.BG_LIGHT, fg=self.FG_MUTED)
        self.pause_btn.config(state=tk.NORMAL, bg="#e6a800", fg="white",
                              text="⏸   PAUSE")
        self.stop_btn.config(state=tk.NORMAL, bg=self.RED, fg="white")
        self.progress_bar["value"] = 0
        self.progress_var.set("Starting...")
        self.status_var.set("Calling session started")
        self.status_dot.config(fg=self.ACCENT)

        # Clear live log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.engine.start_calling()

    def _toggle_pause(self):
        if not self.engine.running:
            return
        if self.engine.paused:
            self.engine.resume_calling()
            self.pause_btn.config(text="⏸   PAUSE", bg="#e6a800", fg="white")
            self.progress_var.set("Resumed")
            self.status_var.set("Calling resumed")
            self.status_dot.config(fg=self.ACCENT)
        else:
            self.engine.pause_calling()
            self.pause_btn.config(text="▶  RESUME", bg=self.ACCENT, fg="white")
            self.progress_var.set("⏸  Paused")
            self.status_var.set("Calling paused — press Resume to continue")
            self.status_dot.config(fg=self.GOLD)

    def _stop_calling(self):
        self.engine.stop_calling()
        self.pause_btn.config(state=tk.DISABLED, bg="#1a2636", fg="#3a5068",
                              text="⏸   PAUSE")
        self.stop_btn.config(state=tk.DISABLED, bg="#331111", fg="#663333")
        self.progress_var.set("Stopping...")
        self.status_var.set("Stop requested — finishing current call...")

    def _append_log(self, text):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)  # auto-scroll to bottom
        self.log_text.config(state=tk.DISABLED)
        # Update status bar with latest log line
        short = text.strip()
        if short:
            self.status_var.set(short[:120])

    def _poll_engine(self):
        """Drain engine message queue and update UI (runs every 100ms)."""
        try:
            while True:
                event_type, data = self.engine.message_queue.get_nowait()
                if event_type == "log":
                    self._append_log(str(data))
                elif event_type == "progress":
                    current, total = data
                    if total > 0:
                        self.progress_bar["maximum"] = total
                        self.progress_bar["value"] = current
                        pct = int(current / total * 100)
                        self.progress_var.set(f"Progress: {current} / {total}  ({pct}%)")
                elif event_type == "complete":
                    self.start_btn.config(state=tk.NORMAL, bg=self.GREEN, fg="white")
                    self.pause_btn.config(state=tk.DISABLED, bg="#1a2636", fg="#3a5068",
                                          text="⏸   PAUSE")
                    self.stop_btn.config(state=tk.DISABLED, bg="#331111", fg="#663333")
                    self.progress_var.set("✓  Complete")
                    self.status_var.set("Calling session complete")
                    self.status_dot.config(fg=self.GREEN)
                    self._refresh_logs_table()
        except q.Empty:
            pass
        self.root.after(100, self._poll_engine)

    # ═══════════════════════════════════════════
    #  TAB 5 — Call Logs
    # ═══════════════════════════════════════════
    def _build_logs_tab(self):
        tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab, text="  📊  Logs  ")

        bar = ttk.Frame(tab)
        bar.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(bar, text="🔄  Refresh", command=self._refresh_logs_table).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Button(bar, text="🗑  Clear Logs", style="Danger.TButton",
                   command=self._clear_logs).pack(side=tk.LEFT)
        self.logs_count_var = tk.StringVar(value="0 calls recorded")
        ttk.Label(bar, textvariable=self.logs_count_var,
                  style="Accent.TLabel").pack(side=tk.RIGHT)

        # Table in a card
        tree_card = tk.Frame(tab, bg=self.BG_INPUT, highlightthickness=1,
                             highlightbackground=self.BORDER)
        tree_card.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "phone_number", "lead_name", "call_status",
                "agent_transferred", "call_duration", "timestamp")
        self.logs_tree = ttk.Treeview(tree_card, columns=cols, show="headings", height=20)
        for cid, text, w in [
            ("id", "#", 40), ("phone_number", "Phone Number", 150),
            ("lead_name", "Lead Name", 160), ("call_status", "Status", 120),
            ("agent_transferred", "Transferred", 100),
            ("call_duration", "Duration", 80), ("timestamp", "Timestamp", 180),
        ]:
            self.logs_tree.heading(cid, text=text)
            self.logs_tree.column(cid, width=w, minwidth=30)

        vsb = ttk.Scrollbar(tree_card, orient=tk.VERTICAL, command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=vsb.set)
        self.logs_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_card.rowconfigure(0, weight=1)
        tree_card.columnconfigure(0, weight=1)

    def _refresh_logs_table(self):
        for item in self.logs_tree.get_children():
            self.logs_tree.delete(item)
        logs = db.get_all_call_logs()
        for lg in logs:
            self.logs_tree.insert("", tk.END, values=(
                lg["id"],
                lg["phone_number"],
                lg["lead_name"],
                lg["call_status"],
                "✓ Yes" if lg["agent_transferred"] else "—",
                f'{lg["call_duration"]}s',
                lg["timestamp"],
            ))
        self.logs_count_var.set(f"📊  {len(logs)} calls recorded")

    def _clear_logs(self):
        if messagebox.askyesno("Clear Logs", "Delete all call log history?"):
            db.clear_call_logs()
            self._refresh_logs_table()

    # ═══════════════════════════════════════════
    #  Cleanup
    # ═══════════════════════════════════════════
    def _on_close(self):
        # Auto-save everything
        for key, var in self.setting_vars.items():
            db.save_setting(key, var.get())
        db.save_setting("tts_message", self.message_text.get("1.0", tk.END).strip())
        if self.engine.running:
            self.engine.stop_calling()
        self.root.destroy()
