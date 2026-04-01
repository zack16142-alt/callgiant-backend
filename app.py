"""
CallGiant - Tkinter GUI Application
Five-tab interface: Leads, Message, Settings, Call Control, Call Logs.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
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
    # ── Dark theme palette ──
    BG          = "#2c3e50"
    BG_LIGHT    = "#34495e"
    BG_DARK     = "#1a252f"
    FG          = "#ffffff"
    FG_DIM      = "#bdc3c7"
    ACCENT      = "#3498db"
    GREEN       = "#27ae60"
    GREEN_HOVER = "#2ecc71"
    RED         = "#c0392b"
    RED_HOVER   = "#e74c3c"
    ENTRY_BG    = "#1a252f"
    ENTRY_FG    = "#ecf0f1"

    def __init__(self, root):
        self.root = root
        self.root.title("CallGiant — Automated Calling System")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=self.BG)

        db.init_db()
        self.engine = CallEngine()

        self._apply_dark_theme()

        # ── Main container ──
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))

        # ── Notebook ──
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._build_leads_tab()
        self._build_message_tab()
        self._build_settings_tab()
        self._build_control_tab()
        self._build_logs_tab()

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Frame(root, bg=self.BG_DARK, height=28)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)
        tk.Label(
            status_bar, textvariable=self.status_var,
            bg=self.BG_DARK, fg=self.FG_DIM,
            font=("Segoe UI", 9), anchor=tk.W, padx=10,
        ).pack(fill=tk.BOTH, expand=True)

        self._load_settings()
        self._setup_auto_save()
        self._refresh_leads_table()
        self._refresh_logs_table()
        self._poll_engine()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────────────────────────
    #  Dark Theme Setup
    # ─────────────────────────────────────────────
    def _apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Global defaults
        style.configure(".",
            background=self.BG, foreground=self.FG,
            fieldbackground=self.ENTRY_BG, borderwidth=0,
            font=("Segoe UI", 10))

        # Frames
        style.configure("TFrame", background=self.BG)
        style.configure("TLabelframe", background=self.BG, foreground=self.FG)
        style.configure("TLabelframe.Label", background=self.BG, foreground=self.ACCENT,
                        font=("Segoe UI", 10, "bold"))

        # Notebook (tabs)
        style.configure("TNotebook", background=self.BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
            background=self.BG_LIGHT, foreground=self.FG_DIM,
            padding=[16, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
            background=[("selected", self.BG), ("active", self.BG)],
            foreground=[("selected", self.FG), ("active", self.FG)])

        # Labels
        style.configure("TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 13, "bold"))
        style.configure("Dim.TLabel", background=self.BG, foreground=self.FG_DIM,
                        font=("Segoe UI", 9))

        # Buttons
        style.configure("TButton",
            background=self.ACCENT, foreground=self.FG,
            font=("Segoe UI", 10, "bold"), padding=[10, 4])
        style.map("TButton",
            background=[("active", "#2980b9"), ("disabled", self.BG_LIGHT)],
            foreground=[("disabled", "#7f8c8d")])

        # Entry
        style.configure("TEntry",
            fieldbackground=self.ENTRY_BG, foreground=self.ENTRY_FG,
            insertcolor=self.ENTRY_FG, borderwidth=1, padding=[4, 3])

        # Treeview
        style.configure("Treeview",
            background=self.BG_DARK, foreground=self.FG,
            fieldbackground=self.BG_DARK, borderwidth=0,
            font=("Segoe UI", 10), rowheight=26)
        style.configure("Treeview.Heading",
            background=self.BG_LIGHT, foreground=self.ACCENT,
            font=("Segoe UI", 10, "bold"), borderwidth=1, relief="flat")
        style.map("Treeview",
            background=[("selected", self.ACCENT)],
            foreground=[("selected", self.FG)])

        # Scrollbar
        style.configure("Vertical.TScrollbar",
            background=self.BG_LIGHT, troughcolor=self.BG_DARK,
            arrowcolor=self.FG_DIM, borderwidth=0)
        style.configure("Horizontal.TScrollbar",
            background=self.BG_LIGHT, troughcolor=self.BG_DARK,
            arrowcolor=self.FG_DIM, borderwidth=0)

        # Progressbar
        style.configure("TProgressbar",
            background=self.GREEN, troughcolor=self.BG_DARK,
            borderwidth=0, thickness=22)

        # Checkbutton / Radiobutton (if used)
        style.configure("TCheckbutton", background=self.BG, foreground=self.FG)
        style.configure("TRadiobutton", background=self.BG, foreground=self.FG)

    # ═══════════════════════════════════════════
    #  TAB 1 — Leads Import
    # ═══════════════════════════════════════════
    def _build_leads_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Leads Import  ")

        bar = ttk.Frame(tab)
        bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(bar, text="Import CSV / XLSX", command=self._import_leads).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="Clear All Leads", command=self._clear_leads).pack(side=tk.LEFT)
        self.leads_count_var = tk.StringVar(value="0 leads")
        ttk.Label(bar, textvariable=self.leads_count_var).pack(side=tk.RIGHT)

        # Table with vertical + horizontal scrollbars
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "phone", "name", "company")
        self.leads_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=20)
        for cid, text, width in [
            ("id", "ID", 50), ("phone", "Phone", 180),
            ("name", "Name", 240), ("company", "Company", 240),
        ]:
            self.leads_tree.heading(cid, text=text)
            self.leads_tree.column(cid, width=width, minwidth=40)

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.leads_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.leads_tree.xview)
        self.leads_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.leads_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

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
        for row in all_rows_raw:
            vals = {k.lower().strip(): v for k, v in row.items()}
            phone = vals.get(phone_col, "").strip()
            if phone:
                leads.append({
                    "phone": phone,
                    "name": vals.get(name_col, "").strip() if name_col else "",
                    "company": vals.get(company_col, "").strip() if company_col else "",
                })
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
        for row in rows[1:]:
            if pi >= len(row):
                continue
            raw = row[pi]
            # Handle numeric phone values (Excel may store as float)
            if isinstance(raw, (int, float)):
                phone = str(int(raw))
            else:
                phone = str(raw or "").strip()
            if phone:
                leads.append({
                    "phone": phone,
                    "name": str(row[ni] or "").strip() if ni is not None and ni < len(row) else "",
                    "company": str(row[ci] or "").strip() if ci is not None and ci < len(row) else "",
                })
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
            bg=self.BG_DARK, fg=self.FG, selectbackground=self.ACCENT,
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
        self.leads_count_var.set(f"{len(leads)} leads")

    def _clear_leads(self):
        if messagebox.askyesno("Clear Leads", "Remove all imported leads?"):
            db.clear_leads()
            self._refresh_leads_table()

    # ═══════════════════════════════════════════
    #  TAB 2 — Message
    # ═══════════════════════════════════════════
    def _build_message_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Message  ")

        ttk.Label(tab, text="TTS Message (spoken to callers when they answer):",
                  style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        self.message_text = tk.Text(tab, wrap=tk.WORD, height=12,
                                    font=("Segoe UI", 11), relief=tk.FLAT, bd=2,
                                    bg=self.BG_DARK, fg=self.ENTRY_FG,
                                    insertbackground=self.ENTRY_FG,
                                    selectbackground=self.ACCENT,
                                    selectforeground=self.FG)
        self.message_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        bar = ttk.Frame(tab)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Test Message (TTS)", command=self._test_tts).pack(side=tk.LEFT)
        ttk.Button(bar, text="Save Message", command=self._save_message).pack(side=tk.LEFT, padx=10)

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
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Call Settings  ")
        self.setting_vars = {}

        # Twilio credentials
        grp1 = ttk.LabelFrame(tab, text="Twilio Credentials", padding=12)
        grp1.pack(fill=tk.X, pady=(0, 10))

        fields = [
            ("twilio_sid",    "Account SID:",          "",     False),
            ("twilio_token",  "Auth Token:",           "",     True),
            ("twilio_number", "Twilio Phone Number:",  "+1…",  False),
            ("agent_number",  "Agent Transfer Number:", "+1…", False),
        ]
        for i, (key, label, ph, secret) in enumerate(fields):
            ttk.Label(grp1, text=label).grid(row=i, column=0, sticky=tk.W, pady=4, padx=(0, 8))
            var = tk.StringVar()
            ent = ttk.Entry(grp1, textvariable=var, width=52, show="*" if secret else "")
            ent.grid(row=i, column=1, sticky=tk.EW, pady=4)
            self.setting_vars[key] = var
        grp1.columnconfigure(1, weight=1)

        # Webhook URL
        grp_wh = ttk.LabelFrame(tab, text="Webhook", padding=12)
        grp_wh.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(grp_wh, text="Webhook URL:").grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        self.setting_vars["webhook_url"] = tk.StringVar(
            value="https://callgiant-backend.onrender.com")
        ttk.Entry(grp_wh, textvariable=self.setting_vars["webhook_url"], width=52).grid(
            row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Label(grp_wh, text="The hosted server that handles Twilio call flow.",
                  style="Dim.TLabel").grid(row=1, column=1, sticky=tk.W)
        grp_wh.columnconfigure(1, weight=1)

        # Call timing
        grp2 = ttk.LabelFrame(tab, text="Timing", padding=12)
        grp2.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(grp2, text="Delay between calls (seconds):").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.setting_vars["call_delay"] = tk.StringVar(value="5")
        ttk.Entry(grp2, textvariable=self.setting_vars["call_delay"], width=10).grid(
            row=0, column=1, sticky=tk.W, pady=4, padx=8)

        ttk.Button(tab, text="Save All Settings", command=self._save_settings).pack(pady=12)

    def _load_settings(self):
        for key, var in self.setting_vars.items():
            val = db.get_setting(key, "")
            if val:
                var.set(val)
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
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Call Control  ")

        # Big buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=16)

        self.start_btn = tk.Button(
            btn_frame, text="▶  START CALLING",
            font=("Segoe UI", 18, "bold"), bg=self.GREEN, fg="white",
            activebackground=self.GREEN_HOVER, activeforeground="white",
            width=18, height=2, cursor="hand2", relief=tk.FLAT, bd=0,
            command=self._start_calling,
        )
        self.start_btn.pack(side=tk.LEFT, padx=8)

        self.stop_btn = tk.Button(
            btn_frame, text="■  STOP CALLING",
            font=("Segoe UI", 18, "bold"), bg=self.RED, fg="white",
            activebackground=self.RED_HOVER, activeforeground="white",
            width=18, height=2, cursor="hand2", relief=tk.FLAT, bd=0,
            state=tk.DISABLED, command=self._stop_calling,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=8)

        # Progress
        prog = ttk.Frame(tab)
        prog.pack(fill=tk.X, pady=(4, 0), padx=4)
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(prog, textvariable=self.progress_var, font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(prog, mode="determinate", length=400)
        self.progress_bar.pack(fill=tk.X, pady=4)

        # Live log
        ttk.Label(tab, text="Live Call Log:", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, pady=(8, 2), padx=4)
        log_frame = ttk.Frame(tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=4)

        self.log_text = tk.Text(
            log_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg="#0d1117", fg="#c9d1d9", insertbackground="#c9d1d9",
            selectbackground=self.ACCENT, selectforeground=self.FG,
            font=("Consolas", 10), relief=tk.FLAT, bd=0, padx=8, pady=6,
        )
        log_sb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
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

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.progress_var.set("Starting...")
        self.status_var.set("Calling session started")

        # Clear live log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.engine.start_calling()

    def _stop_calling(self):
        self.engine.stop_calling()
        self.stop_btn.config(state=tk.DISABLED)
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
                    self.start_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                    self.progress_var.set("Complete")
                    self.status_var.set("Calling session complete")
                    self._refresh_logs_table()
        except q.Empty:
            pass
        self.root.after(100, self._poll_engine)

    # ═══════════════════════════════════════════
    #  TAB 5 — Call Logs
    # ═══════════════════════════════════════════
    def _build_logs_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="  Call Logs  ")

        bar = ttk.Frame(tab)
        bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(bar, text="Refresh", command=self._refresh_logs_table).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(bar, text="Clear Logs", command=self._clear_logs).pack(side=tk.LEFT)
        self.logs_count_var = tk.StringVar(value="0 calls")
        ttk.Label(bar, textvariable=self.logs_count_var).pack(side=tk.RIGHT)

        cols = ("id", "phone_number", "lead_name", "call_status",
                "agent_transferred", "call_duration", "timestamp")
        self.logs_tree = ttk.Treeview(tab, columns=cols, show="headings", height=20)
        for cid, text, w in [
            ("id", "ID", 40), ("phone_number", "Phone Number", 140),
            ("lead_name", "Lead Name", 150), ("call_status", "Call Status", 110),
            ("agent_transferred", "Agent Transfer", 100),
            ("call_duration", "Duration", 80), ("timestamp", "Timestamp", 170),
        ]:
            self.logs_tree.heading(cid, text=text)
            self.logs_tree.column(cid, width=w, minwidth=30)

        vsb = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=vsb.set)
        self.logs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

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
                "Yes" if lg["agent_transferred"] else "No",
                f'{lg["call_duration"]}s',
                lg["timestamp"],
            ))
        self.logs_count_var.set(f"{len(logs)} calls")

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
