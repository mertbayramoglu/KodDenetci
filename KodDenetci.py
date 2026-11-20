# -*- coding: utf-8 -*-
"""
Kod Denetçi / CodeAuditor - masaüstü arayüzü (tkinter), Türkçe + English.
Seçilen proje klasöründeki tüm kod dosyalarını okur, dosya dosya hataları listeler ve
her dosya için düzeltme prompt'ları üretir. Veritabanı ve dosyalar yereldir; internet gerekmez.

Komut satırı:  KodDenetci.py --cli <klasör> [--prompts <çıktı klasörü>] [--lang tr|en]
"""
import os
import sys
import threading
import queue
import subprocess
import webbrowser

import kd_core as core
import kd_i18n as i18n

if "--cli" in sys.argv:          # arayüzsüz kip: tkinter gerekmez
    core.cli_main(sys.argv)
    sys.exit(0)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

SEV_COLORS = {"critical": "#fde2e2", "error": "#fdeccf", "warning": "#fff6cc", "info": "#eef2f7"}


def open_path(p, trusted=False):
    """trusted=False: taranan projeden gelen dosya; betik/HTML ise çalıştırmak yerine metin olarak açılır."""
    try:
        if sys.platform.startswith("win"):
            if not trusted and os.path.isfile(p) and core.is_risky_to_open(p):
                subprocess.Popen(["notepad.exe", os.path.normpath(p)])
            else:
                os.startfile(p)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as ex:
        messagebox.showerror("Error", str(ex))


def reveal(p):
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
    else:
        open_path(os.path.dirname(p), trusted=True)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.conn = core.open_db()
        self.st = core.get_settings(self.conn)
        self.lang = i18n.resolve(self.st.get("lang"))
        self.q = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.root_dir = self.st.get("last_dir", "")
        self.scan_id = None
        self.files = []          # sqlite satırları (sözlük)
        self.issues = []
        self.crit_rows = {}
        self.cur_file = None
        self.parts = []
        self.guide_win = None
        self._warn = ""
        self._style()
        self._build()
        self.bind("<F1>", lambda _e: self.show_guide())
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll)
        if self.root_dir:
            self.dir_var.set(self.root_dir)
            self._load_last_scan()

    # ---------------- yardımcılar ----------------
    def t(self, key, **kw):
        return i18n.t(key, self.lang, **kw)

    def plang(self):
        """Prompt ve rapor dili."""
        p = (self.st.get("prompt_lang") or "auto").lower()
        return self.lang if p == "auto" else i18n.resolve(p)

    def sev(self, s):
        return i18n.SEV[self.lang][s]

    def tx(self, text):
        return i18n.tx(text, self.lang)

    def lang_label(self, code):
        return i18n.LANG_LABEL[self.lang].get(code, code)

    # ---------------- görünüm ----------------
    def _style(self):
        s = ttk.Style(self)
        for t in ("vista", "clam"):
            if t in s.theme_names():
                s.theme_use(t)
                break
        self.option_add("*Font", "{Segoe UI} 10")
        s.configure(".", font=("Segoe UI", 10))
        s.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(4, 4))
        s.configure("TNotebook.Tab", padding=(16, 7), font=("Segoe UI", 10))
        s.configure("TButton", padding=(10, 4))
        s.configure("Big.TButton", padding=(18, 6), font=("Segoe UI", 10, "bold"))
        s.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        self.mono = ("Consolas", 10) if sys.platform.startswith("win") else ("DejaVu Sans Mono", 10)

    def _build(self):
        """Tüm arayüzü (yeniden) kurar; dil değişince de çağrılır."""
        self.title(f"{i18n.APP_NAME[self.lang]} {core.APP_VER}")
        if not self.winfo_ismapped():
            self.geometry("1360x840")
        self.minsize(1000, 600)
        self._icon()
        self._menu()
        self._header()
        self._top()
        self._body()
        self._status()

    def rebuild_ui(self):
        keep = self.dir_var.get() if hasattr(self, "dir_var") else ""
        for w in self.winfo_children():
            w.destroy()
        self.guide_win = None
        self._build()
        self.dir_var.set(keep)
        self.cur_file = None
        self.parts = []
        if self.scan_id:
            self.load_scan(self.scan_id)
        else:
            self.refresh_history()

    def _icon(self):
        try:
            ico = os.path.join(core.app_dir(), "kd.ico")
            if sys.platform.startswith("win") and os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:  # kd-ignore (en iyi çaba: simge yoksa devam et)
            pass

    def _header(self):
        h = tk.Frame(self, bg="#1e3a8a")
        h.pack(fill="x")
        tk.Label(h, text=i18n.APP_NAME[self.lang], bg="#1e3a8a", fg="white", font=("Segoe UI", 16, "bold")).pack(side="left", padx=(14, 8), pady=8)
        tk.Label(h, text=i18n.APP_TAGLINE[self.lang], bg="#1e3a8a", fg="#bfdbfe", font=("Segoe UI", 10)).pack(side="left", pady=8)
        tk.Label(h, text=f"v{core.APP_VER}", bg="#1e3a8a", fg="#93c5fd", font=("Segoe UI", 9)).pack(side="right", padx=14)

    def _menu(self):
        m = tk.Menu(self)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label=self.t("m_pick"), command=self.pick_dir)
        f.add_separator()
        f.add_command(label=self.t("m_rep_md"), command=lambda: self.export_report("md"))
        f.add_command(label=self.t("m_rep_html"), command=lambda: self.export_report("html"))
        f.add_command(label=self.t("m_prompts"), command=self.export_all_prompts)
        f.add_separator()
        f.add_command(label=self.t("m_datadir"), command=lambda: open_path(core.data_dir(), trusted=True))
        f.add_command(label=self.t("m_exit"), command=self._close)
        m.add_cascade(label=self.t("m_file"), menu=f)
        a = tk.Menu(m, tearoff=0)
        a.add_command(label=self.t("m_settings_item"), command=self.settings_dialog)
        m.add_cascade(label=self.t("m_settings"), menu=a)
        lg = tk.Menu(m, tearoff=0)
        lg.add_command(label="Türkçe", command=lambda: self.set_language("tr"))
        lg.add_command(label="English", command=lambda: self.set_language("en"))
        lg.add_command(label=self.t("opt_auto"), command=lambda: self.set_language("auto"))
        m.add_cascade(label="Dil / Language", menu=lg)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label=self.t("m_guide"), command=self.show_guide, accelerator="F1")
        h.add_command(label=self.t("m_feedback"), command=self.feedback_dialog)
        h.add_command(label=self.t("m_site"), command=lambda: webbrowser.open(core.REPO_URL))
        h.add_separator()
        h.add_command(label=self.t("m_about"), command=self.about)
        m.add_cascade(label=self.t("m_help"), menu=h)
        self.config(menu=m)

    def _top(self):
        fr = ttk.Frame(self, padding=(8, 8, 8, 2))
        fr.pack(fill="x")
        ttk.Label(fr, text=self.t("lbl_dir")).pack(side="left")
        self.dir_var = tk.StringVar()
        e = ttk.Entry(fr, textvariable=self.dir_var)
        e.pack(side="left", fill="x", expand=True, padx=6)
        e.bind("<Return>", lambda _e: self.start_scan())
        ttk.Button(fr, text=self.t("b_pick"), command=self.pick_dir).pack(side="left")
        self.btn_scan = ttk.Button(fr, text=self.t("b_scan"), style="Big.TButton", command=self.start_scan)
        self.btn_scan.pack(side="left", padx=(8, 2))
        self.btn_stop = ttk.Button(fr, text=self.t("b_stop"), command=lambda: self.cancel.set(), state="disabled")
        self.btn_stop.pack(side="left")
        self.pb = ttk.Progressbar(self, mode="determinate")
        self.pb.pack(fill="x", padx=8, pady=(2, 4))

    def _body(self):
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=8, pady=4)
        # ---- sol: dosya listesi
        left = ttk.Frame(pw)
        pw.add(left, weight=2)
        fl = ttk.Frame(left)
        fl.pack(fill="x")
        self.filter_cb = ttk.Combobox(fl, state="readonly", width=20,
                                      values=[self.t("f_all"), self.t("f_with"), self.t("f_crit_err"), self.t("f_crit")])
        self.filter_cb.pack(side="left")
        self.filter_cb.current(1)
        self.filter_cb.bind("<<ComboboxSelected>>", lambda _e: self.fill_files())
        self.search_var = tk.StringVar()
        se = ttk.Entry(fl, textvariable=self.search_var)
        se.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.search_var.trace_add("write", lambda *_: self.fill_files())
        ab = i18n.SEV_ABBR[self.lang]
        cols = ("lang", "lines", "tok", "c", "e", "w", "i")
        self.tf = ttk.Treeview(left, columns=cols, selectmode="browse")
        self.tf.heading("#0", text=self.t("col_file"))
        self.tf.column("#0", width=300, stretch=True)
        for c, tx, w in (("lang", self.t("col_lang"), 60), ("lines", self.t("col_lines"), 55), ("tok", self.t("col_tok"), 65),
                         ("c", ab["critical"], 32), ("e", ab["error"], 32), ("w", ab["warning"], 32), ("i", ab["info"], 32)):
            self.tf.heading(c, text=tx)
            self.tf.column(c, width=w, anchor="e" if c != "lang" else "w", stretch=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tf.yview)
        self.tf.configure(yscrollcommand=sb.set)
        ttk.Label(left, text=self.t("legend"), foreground="#555", wraplength=420, justify="left").pack(side="bottom", anchor="w", pady=(4, 0))
        self.tf.pack(side="left", fill="both", expand=True, pady=(4, 0))
        sb.pack(side="right", fill="y", pady=(4, 0))
        for k, col in SEV_COLORS.items():
            self.tf.tag_configure(k, background=col)
        self.tf.bind("<<TreeviewSelect>>", self.on_file_select)
        self.tf.bind("<Double-1>", lambda _e: self.open_current())
        self.menu_f = tk.Menu(self, tearoff=0)
        self.menu_f.add_command(label=self.t("ctx_open"), command=self.open_current)
        self.menu_f.add_command(label=self.t("ctx_reveal"), command=self.reveal_current)
        self.menu_f.add_command(label=self.t("ctx_copy"), command=self.copy_prompt)
        self.tf.bind("<Button-3>", self._ctx)
        # ---- sağ: sekmeler
        self.nb = ttk.Notebook(pw)
        pw.add(self.nb, weight=3)
        self._tab_issues()
        self._tab_critical()
        self._tab_prompt()
        self._tab_summary()
        self._tab_history()

    def _tab_issues(self):
        t = ttk.Frame(self.nb)
        self.nb.add(t, text=self.t("tab_findings"))
        self.lbl_file = ttk.Label(t, text=self.t("pick_file"), font=("Segoe UI", 10, "bold"))
        self.lbl_file.pack(anchor="w", padx=6, pady=4)
        pw = ttk.PanedWindow(t, orient="vertical")
        pw.pack(fill="both", expand=True)
        fr = ttk.Frame(pw)
        pw.add(fr, weight=3)
        self.ti = ttk.Treeview(fr, columns=("sev", "line", "rule", "msg"), show="headings", selectmode="browse")
        for c, tx, w in (("sev", self.t("col_sev"), 80), ("line", self.t("col_line"), 55), ("rule", self.t("col_rule"), 70),
                         ("msg", self.t("col_desc"), 420)):
            self.ti.heading(c, text=tx)
            self.ti.column(c, width=w, stretch=(c == "msg"), anchor="e" if c == "line" else "w")
        sb = ttk.Scrollbar(fr, orient="vertical", command=self.ti.yview)
        self.ti.configure(yscrollcommand=sb.set)
        self.ti.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for k, col in SEV_COLORS.items():
            self.ti.tag_configure(k, background=col)
        self.ti.bind("<<TreeviewSelect>>", self.on_issue_select)
        self.detail = tk.Text(pw, height=8, wrap="word", font=self.mono, state="disabled", bg="#fafafa")
        pw.add(self.detail, weight=1)

    def _tab_critical(self):
        t = ttk.Frame(self.nb)
        self.fr_crit = t
        self.nb.add(t, text=self.t("tab_crit"))
        bar = ttk.Frame(t)
        bar.pack(fill="x", padx=6, pady=6)
        self.crit_cb = ttk.Combobox(bar, state="readonly", width=18, values=[self.t("c_mode_crit"), self.t("c_mode_both")])
        self.crit_cb.pack(side="left")
        self.crit_cb.current(0)
        self.crit_cb.bind("<<ComboboxSelected>>", lambda _e: self.fill_critical())
        self.lbl_crit = ttk.Label(bar, text="")
        self.lbl_crit.pack(side="left", padx=10)
        ttk.Button(bar, text=self.t("c_copy"), command=self.copy_critical).pack(side="right")
        fr = ttk.Frame(t)
        fr.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        cols = ("file", "line", "rule", "msg", "code")
        self.tc = ttk.Treeview(fr, columns=cols, show="headings", selectmode="browse")
        for c, tx, w, st in (("file", self.t("col_file_short"), 230, False), ("line", self.t("col_line"), 55, False),
                             ("rule", self.t("col_rule"), 70, False), ("msg", self.t("col_desc"), 330, True),
                             ("code", self.t("col_code"), 300, True)):
            self.tc.heading(c, text=tx)
            self.tc.column(c, width=w, stretch=st, anchor="e" if c == "line" else "w")
        sy = ttk.Scrollbar(fr, orient="vertical", command=self.tc.yview)
        sx = ttk.Scrollbar(fr, orient="horizontal", command=self.tc.xview)
        self.tc.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.tc.pack(side="left", fill="both", expand=True)
        for k, col in SEV_COLORS.items():
            self.tc.tag_configure(k, background=col)
        self.tc.bind("<Double-1>", self.jump_critical)
        ttk.Label(t, text=self.t("c_hint")).pack(anchor="w", padx=8, pady=(0, 6))

    def _tab_prompt(self):
        t = ttk.Frame(self.nb)
        self.nb.add(t, text=self.t("tab_prompt"))
        bar = ttk.Frame(t)
        bar.pack(fill="x", padx=6, pady=4)
        self.part_var = tk.StringVar()
        self.part_cb = ttk.Combobox(bar, textvariable=self.part_var, state="readonly", width=34)
        self.part_cb.pack(side="left")
        self.part_cb.bind("<<ComboboxSelected>>", lambda _e: self.show_part())
        self.lbl_tok = ttk.Label(bar, text="")
        self.lbl_tok.pack(side="left", padx=10)
        ttk.Button(bar, text=self.t("p_copy"), command=self.copy_prompt).pack(side="right")
        ttk.Button(bar, text=self.t("p_save"), command=self.save_prompt).pack(side="right", padx=4)
        fr = ttk.Frame(t)
        fr.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.txt_prompt = tk.Text(fr, wrap="none", font=self.mono, undo=False)
        sy = ttk.Scrollbar(fr, orient="vertical", command=self.txt_prompt.yview)
        sx = ttk.Scrollbar(fr, orient="horizontal", command=self.txt_prompt.xview)
        self.txt_prompt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.txt_prompt.pack(side="left", fill="both", expand=True)

    def _tab_summary(self):
        t = ttk.Frame(self.nb)
        self.fr_sum = t
        self.nb.add(t, text=self.t("tab_summary"))
        self.txt_sum = tk.Text(t, wrap="word", height=16, font=("Segoe UI", 10), state="disabled", bg="#fafafa")
        self.txt_sum.pack(fill="both", expand=True, padx=6, pady=6)
        lf = ttk.LabelFrame(t, text=self.t("note_title"))
        lf.pack(fill="x", padx=6, pady=4)
        self.txt_note = tk.Text(lf, height=3, wrap="word")
        self.txt_note.pack(fill="x", padx=4, pady=4)
        row = ttk.Frame(lf)
        row.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(row, text=self.t("note_save"), command=self.save_note).pack(side="left")
        ttk.Button(row, text=self.t("proj_prompt"), command=self.project_prompt).pack(side="right")

    def _tab_history(self):
        t = ttk.Frame(self.nb)
        self.nb.add(t, text=self.t("tab_history"))
        ab = i18n.SEV[self.lang]
        self.th = ttk.Treeview(t, columns=("date", "files", "c", "e", "w", "i", "new", "fixed"), show="headings", selectmode="browse")
        for c, tx, w in (("date", self.t("h_date"), 130), ("files", self.t("h_files"), 60), ("c", ab["critical"], 60),
                         ("e", ab["error"], 55), ("w", ab["warning"], 60), ("i", ab["info"], 55),
                         ("new", self.t("h_new"), 55), ("fixed", self.t("h_fixed"), 70)):
            self.th.heading(c, text=tx)
            self.th.column(c, width=w, anchor="w" if c == "date" else "e")
        self.th.pack(fill="both", expand=True, padx=6, pady=6)
        row = ttk.Frame(t)
        row.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(row, text=self.t("h_open"), command=self.open_history).pack(side="left")
        ttk.Button(row, text=self.t("h_delete"), command=self.delete_history).pack(side="left", padx=6)

    def _status(self):
        self.status = tk.StringVar(value=self.t("st_ready"))
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w", padding=(6, 2)).pack(fill="x", side="bottom")

    # ---------------- dil ----------------
    def set_language(self, code):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo(self.t("busy_title"), self.t("busy_msg"))
            return
        core.set_setting(self.conn, "lang", code)
        self.st["lang"] = code
        self.lang = i18n.resolve(code)
        self.rebuild_ui()

    # ---------------- tarama ----------------
    def pick_dir(self):
        d = filedialog.askdirectory(title=self.t("dlg_pick_dir"), initialdir=self.dir_var.get() or None)
        if d:
            self.dir_var.set(os.path.normpath(d))
            self.start_scan()

    def start_scan(self):
        d = self.dir_var.get().strip().strip('"')
        if not os.path.isdir(d):
            messagebox.showwarning(self.t("no_dir_title"), self.t("no_dir_msg"))
            return
        if self.worker and self.worker.is_alive():
            return
        self.root_dir = os.path.normpath(d)
        core.set_setting(self.conn, "last_dir", self.root_dir)
        self.cancel.clear()
        self.btn_scan.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.pb.config(value=0, maximum=100)
        self.status.set(self.t("st_listing"))
        settings = dict(self.st)
        root = self.root_dir

        def work():
            try:
                conn = core.open_db()
                res = core.scan_project(root, conn, settings,
                                        progress=lambda i, n, rel: self.q.put(("p", i, n, rel)),
                                        cancel=self.cancel)
                conn.close()
                self.q.put(("done", res))
            except Exception as ex:
                self.q.put(("err", str(ex)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "p":
                    _, i, n, rel = m
                    self.pb.config(maximum=max(n, 1), value=i)
                    self.status.set(self.t("st_scanning", i=i, n=n, rel=rel))
                elif m[0] == "done":
                    r = m[1]
                    self.btn_scan.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    self.scan_id = r["scan_id"]
                    self.load_scan(self.scan_id)
                    msg = self.t("st_cancelled" if r.get("cancelled") else "st_done", f=r["files"], i=r["issues"],
                                 new=r["new"], fixed=r["fixed"], t=f"{r['tokens']:,}")
                    if r.get("ignored"):
                        msg += self.t("st_ignored", n=r["ignored"])
                    self.status.set(msg)
                    self.nb.select(0)
                elif m[0] == "err":
                    self.btn_scan.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    messagebox.showerror(self.t("err_scan_title"), m[1])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _load_last_scan(self):
        r = self.conn.execute("SELECT id FROM scans WHERE project=? AND finished IS NOT NULL ORDER BY id DESC LIMIT 1",
                              (self.root_dir,)).fetchone()
        if r:
            self.scan_id = r["id"]
            self.load_scan(self.scan_id)
        else:
            self.refresh_history()

    def load_scan(self, sid):
        self.scan_id = sid
        self.files = [dict(r) for r in self.conn.execute("SELECT * FROM files WHERE scan_id=? ORDER BY risk DESC, rel", (sid,))]
        self.fill_files()
        self.fill_summary()
        self.fill_critical()
        self.refresh_history()
        self.txt_note.delete("1.0", "end")
        self.txt_note.insert("1.0", core.get_note(self.conn, self.root_dir))
        self.clear_detail()

    # ---------------- listeler ----------------
    def fill_files(self):
        self.tf.delete(*self.tf.get_children())
        mode = self.filter_cb.current()          # 0 tümü · 1 bulgusu olanlar · 2 kritik+hata · 3 yalnız kritik
        q = self.search_var.get().strip().lower()
        for f in self.files:
            if mode == 1 and not (f["c"] or f["e"] or f["w"] or f["i"]):
                continue
            if mode == 2 and not (f["c"] or f["e"]):
                continue
            if mode == 3 and not f["c"]:
                continue
            if q and q not in f["rel"].lower():
                continue
            tag = "critical" if f["c"] else "error" if f["e"] else "warning" if f["w"] else "info" if f["i"] else ""
            self.tf.insert("", "end", iid=str(f["id"]), text=f["rel"], tags=(tag,) if tag else (),
                           values=(f["lang"], f["lines"], f["tokens"], f["c"], f["e"], f["w"], f["i"]))

    def clear_detail(self):
        self.cur_file = None
        self.issues = []
        self.ti.delete(*self.ti.get_children())
        self.lbl_file.config(text=self.t("pick_file"))
        self._set_text(self.detail, "")
        self.parts = []
        self.part_cb.config(values=[])
        self.part_var.set("")
        self.txt_prompt.delete("1.0", "end")
        self.lbl_tok.config(text="")

    def _set_text(self, w, s):
        w.config(state="normal")
        w.delete("1.0", "end")
        w.insert("1.0", s)
        w.config(state="disabled")

    def on_file_select(self, _e=None):
        sel = self.tf.selection()
        if not sel:
            return
        fid = int(sel[0])
        f = next((x for x in self.files if x["id"] == fid), None)
        if not f:
            return
        self.cur_file = f
        self.lbl_file.config(text=self.t("file_hdr", rel=f["rel"], lang=self.lang_label(f["lang"]), lines=f["lines"],
                                         tok=f["tokens"], enc=f["enc"] or "-"))
        self.ti.delete(*self.ti.get_children())
        self.issues = [dict(r) for r in self.conn.execute("SELECT * FROM issues WHERE file_id=? ORDER BY line", (fid,))]
        for it in self.issues:
            self.ti.insert("", "end", iid=str(it["id"]), tags=(it["severity"],),
                           values=(self.sev(it["severity"]) + (" ★" if it["isnew"] else ""), it["line"] or "-", it["rule"], self.tx(it["message"])))
        self._set_text(self.detail, "")
        self.make_prompts()

    def on_issue_select(self, _e=None):
        sel = self.ti.selection()
        if not sel:
            return
        it = next((x for x in self.issues if x["id"] == int(sel[0])), None)
        if not it:
            return
        s = self.t("d_head", sev=self.sev(it["severity"]), rule=it["rule"], line=it["line"] or "-", col=it["col"] or "-")
        if it["isnew"]:
            s += "   " + self.t("d_new")
        s += f"\n\n{self.tx(it['message'])}\n\n{self.t('d_code')}\n  {it['snippet']}\n\n{self.t('d_fix')}\n  {self.tx(it['fix'])}"
        self._set_text(self.detail, s)

    # ---------------- kritik hatalar ----------------
    def fill_critical(self):
        self.tc.delete(*self.tc.get_children())
        self.crit_rows = {}
        if not self.scan_id:
            self.lbl_crit.config(text="")
            self.nb.tab(self.fr_crit, text=self.t("tab_crit"))
            return
        sevs = ("critical",) if self.crit_cb.current() == 0 else ("critical", "error")
        marks = ",".join("?" * len(sevs))
        rows = self.conn.execute(
            "SELECT i.*, f.rel, f.risk FROM issues i JOIN files f ON f.id=i.file_id "
            f"WHERE i.scan_id=? AND i.severity IN ({marks}) ORDER BY i.severity, f.risk DESC, f.rel, i.line",
            (self.scan_id,) + sevs).fetchall()
        for r in rows:
            self.crit_rows[str(r["id"])] = r
            self.tc.insert("", "end", iid=str(r["id"]), tags=(r["severity"],),
                           values=(r["rel"], r["line"] or "-", r["rule"], self.tx(r["message"]), r["snippet"]))
        nfiles = len({r["file_id"] for r in rows})
        self.lbl_crit.config(text=self.t("c_count", n=len(rows), f=nfiles) if rows else self.t("c_none"))
        sc = self.conn.execute("SELECT crit FROM scans WHERE id=?", (self.scan_id,)).fetchone()
        self.nb.tab(self.fr_crit, text=self.t("tab_crit_n", n=sc["crit"] if sc else 0))

    def copy_critical(self):
        if not self.crit_rows:
            return
        L = []
        for r in self.crit_rows.values():
            L.append(f"[{self.sev(r['severity'])}] {r['rel']}:{r['line'] or '-'}  {r['rule']} - {self.tx(r['message'])}")
            if r["snippet"]:
                L.append(f"    {r['snippet']}")
        self.clipboard_clear()
        self.clipboard_append("\n".join(L))
        self.status.set(self.t("c_copied", n=len(self.crit_rows)))

    def jump_critical(self, _e=None):
        sel = self.tc.selection()
        r = self.crit_rows.get(sel[0]) if sel else None
        if not r:
            return
        self.filter_cb.current(0)
        self.search_var.set("")
        self.fill_files()
        fid = str(r["file_id"])
        if fid in self.tf.get_children():
            self.tf.selection_set(fid)
            self.tf.see(fid)
        self.nb.select(0)

        def pick():
            iid = str(r["id"])
            if self.ti.exists(iid):
                self.ti.selection_set(iid)
                self.ti.see(iid)
                self.on_issue_select()
        self.after(80, pick)   # <<TreeviewSelect>> olayı işlendikten sonra

    # ---------------- prompt ----------------
    def make_prompts(self):
        f = self.cur_file
        self.parts = []
        self.txt_prompt.delete("1.0", "end")
        if not f:
            return
        path = os.path.join(self.root_dir, f["rel"])
        try:
            text, _, raw = core.read_text(path)
        except OSError as ex:
            self.txt_prompt.insert("1.0", self.t("p_unreadable", err=ex))
            return
        if text is None:
            return
        pl = self.plang()
        self._warn = ""
        if core.sha1_of(raw) != f["sha1"]:
            self._warn = i18n.PROMPT[pl]["stale"] + "\n\n"
        if not self.issues:
            self.txt_prompt.insert("1.0", self.t("p_nofind"))
            self.part_cb.config(values=[])
            self.part_var.set("")
            self.lbl_tok.config(text="")
            return
        note = core.get_note(self.conn, self.root_dir)
        self.parts = core.build_prompts(os.path.basename(self.root_dir), f["rel"], f["lang"], text, self.issues,
                                        int(self.st["budget"]), int(self.st["ctx"]), note, pl)
        self.part_cb.config(values=[p["title"] for p in self.parts])
        self.part_cb.current(0)
        self.show_part()

    def show_part(self):
        i = self.part_cb.current()
        if i < 0 or i >= len(self.parts):
            return
        p = self.parts[i]
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", self._warn + p["text"])
        self.lbl_tok.config(text=self.t("p_tokens", n=f"{p['tokens']:,}", b=f"{int(self.st['budget']):,}"))

    def copy_prompt(self):
        txt = self.txt_prompt.get("1.0", "end").rstrip()
        if not txt:
            return
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.status.set(self.t("p_copied"))

    def save_prompt(self):
        txt = self.txt_prompt.get("1.0", "end").rstrip()
        if not txt:
            return
        name = core.safe_name(self.cur_file["rel"]) + ".md" if self.cur_file else "prompt.md"
        p = filedialog.asksaveasfilename(defaultextension=".md", initialfile=name,
                                         filetypes=[("Markdown", "*.md"), (self.t("ft_text"), "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(txt)

    def project_prompt(self):
        if not self.files:
            return
        txt = core.build_project_prompt(os.path.basename(self.root_dir), [f for f in self.files if f["c"] or f["e"] or f["w"]],
                                        core.get_note(self.conn, self.root_dir), ui=self.plang())
        w = tk.Toplevel(self)
        w.title(self.t("proj_win"))
        w.geometry("800x520")
        t = tk.Text(w, wrap="word", font=self.mono)
        t.pack(fill="both", expand=True, padx=6, pady=6)
        t.insert("1.0", txt)

        def cp():
            self.clipboard_clear()
            self.clipboard_append(t.get("1.0", "end").rstrip())
            self.status.set(self.t("proj_copied"))
        ttk.Button(w, text=self.t("p_copy"), command=cp).pack(pady=(0, 6))

    # ---------------- özet / not / geçmiş ----------------
    def fill_summary(self):
        sc = self.conn.execute("SELECT * FROM scans WHERE id=?", (self.scan_id,)).fetchone()
        if not sc:
            return
        rules = self.conn.execute(
            "SELECT rule, severity, COUNT(*) n FROM issues WHERE scan_id=? GROUP BY rule, severity ORDER BY n DESC LIMIT 12",
            (self.scan_id,)).fetchall()
        langs = self.conn.execute(
            "SELECT lang, COUNT(*) n, SUM(tokens) t FROM files WHERE scan_id=? GROUP BY lang ORDER BY t DESC", (self.scan_id,)).fetchall()
        L = [f"{self.t('s_project')}: {sc['project']}", f"{self.t('s_date')}: {core.fmt_time(sc['finished'])}",
             self.t("s_files", n=sc["n_files"], s=sc["skipped"], t=f"{sc['tokens']:,}"), "",
             self.t("s_counts", c=sc["crit"], e=sc["err"], w=sc["warn"], i=sc["info"]),
             self.t("s_delta", n=sc["new_issues"], f=sc["fixed_issues"]), "", self.t("s_rules")]
        for r in rules:
            L.append(f"   {r['n']:>4} × {r['rule']}  ({self.sev(r['severity'])})")
        L += ["", self.t("s_langs")]
        for r in langs:
            L.append("   " + self.t("s_lang_line", lang=self.lang_label(r["lang"]), n=r["n"], t=f"{r['t']:,}"))
        self._set_text(self.txt_sum, "\n".join(L))

    def save_note(self):
        core.set_note(self.conn, self.root_dir, self.txt_note.get("1.0", "end").strip())
        self.status.set(self.t("note_saved"))
        if self.cur_file:
            self.make_prompts()

    def refresh_history(self):
        self.th.delete(*self.th.get_children())
        for s in self.conn.execute("SELECT * FROM scans WHERE project=? AND finished IS NOT NULL ORDER BY id DESC", (self.root_dir,)):
            self.th.insert("", "end", iid=str(s["id"]), values=(core.fmt_time(s["finished"]), s["n_files"], s["crit"], s["err"],
                                                                 s["warn"], s["info"], s["new_issues"], s["fixed_issues"]))

    def open_history(self):
        sel = self.th.selection()
        if sel:
            self.load_scan(int(sel[0]))
            self.nb.select(self.fr_sum)

    def delete_history(self):
        sel = self.th.selection()
        if sel and messagebox.askyesno(self.t("h_del_title"), self.t("h_del_q")):
            sid = int(sel[0])
            core.delete_scan(self.conn, sid)
            if sid == self.scan_id:
                self.scan_id = None
                self.files = []
                self.fill_files()
                self.clear_detail()
                self.fill_critical()
            self.refresh_history()

    # ---------------- dışa aktarma ----------------
    def _need_scan(self):
        if not self.scan_id:
            messagebox.showinfo(self.t("no_scan_title"), self.t("no_scan_msg"))
            return False
        return True

    def export_report(self, kind):
        if not self._need_scan():
            return
        p = filedialog.asksaveasfilename(defaultextension="." + kind, initialfile=f"{self.t('rep_file')}.{kind}",
                                         initialdir=core.data_dir(),
                                         filetypes=[("Markdown", "*.md")] if kind == "md" else [("HTML", "*.html")])
        if not p:
            return
        pl = self.plang()
        s = core.report_markdown(self.conn, self.scan_id, pl) if kind == "md" else core.report_html(self.conn, self.scan_id, pl)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(s)
        self.status.set(self.t("rep_saved", p=p))
        if kind == "html":
            open_path(p, trusted=True)

    def export_all_prompts(self):
        if not self._need_scan():
            return
        d = filedialog.askdirectory(title=self.t("dlg_prompts_dir"), initialdir=core.data_dir())
        if not d:
            return
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            n = core.export_prompts(self.conn, self.scan_id, d, os.path.basename(self.root_dir), self.root_dir, self.st,
                                    core.get_note(self.conn, self.root_dir), self.plang())
        finally:
            self.config(cursor="")
        messagebox.showinfo(self.t("done_title"), self.t("prompts_done", n=n))
        open_path(d, trusted=True)

    # ---------------- sağ tık / dosya işlemleri ----------------
    def _ctx(self, ev):
        iid = self.tf.identify_row(ev.y)
        if iid:
            self.tf.selection_set(iid)
            self.menu_f.tk_popup(ev.x_root, ev.y_root)

    def open_current(self):
        if self.cur_file:
            open_path(os.path.join(self.root_dir, self.cur_file["rel"]))

    def reveal_current(self):
        if self.cur_file:
            reveal(os.path.join(self.root_dir, self.cur_file["rel"]))

    # ---------------- ayarlar ----------------
    def settings_dialog(self):
        w = tk.Toplevel(self)
        w.title(self.t("set_title"))
        w.transient(self)
        w.grab_set()
        w.columnconfigure(1, weight=1)
        codes = ["auto", "tr", "en"]
        cur_l = codes.index(self.st.get("lang", "auto")) if self.st.get("lang", "auto") in codes else 0
        cur_p = codes.index(self.st.get("prompt_lang", "auto")) if self.st.get("prompt_lang", "auto") in codes else 0
        r = 0
        ttk.Label(w, text=self.t("set_lang"), font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="nw", padx=10, pady=(10, 0))
        cb_l = ttk.Combobox(w, state="readonly", width=24, values=[self.t("opt_auto"), "Türkçe", "English"])
        cb_l.grid(row=r, column=1, sticky="w", padx=10, pady=(10, 0))
        cb_l.current(cur_l)
        ttk.Label(w, text=self.t("set_lang_h"), wraplength=420, foreground="#555", justify="left").grid(row=r + 1, column=1, sticky="w", padx=10)
        r += 2
        ttk.Label(w, text=self.t("set_plang"), font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="nw", padx=10, pady=(10, 0))
        cb_p = ttk.Combobox(w, state="readonly", width=24, values=[self.t("opt_same"), "Türkçe", "English"])
        cb_p.grid(row=r, column=1, sticky="w", padx=10, pady=(10, 0))
        cb_p.current(cur_p)
        ttk.Label(w, text=self.t("set_plang_h"), wraplength=420, foreground="#555", justify="left").grid(row=r + 1, column=1, sticky="w", padx=10)
        r += 2
        vars_ = {}
        for k in ("budget", "ctx", "max_kb", "exclude"):
            ttk.Label(w, text=self.t(f"set_{k}"), font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="nw", padx=10, pady=(10, 0))
            v = tk.StringVar(value=self.st.get(k, ""))
            vars_[k] = v
            ttk.Entry(w, textvariable=v, width=56 if k == "exclude" else 14).grid(row=r, column=1, sticky="w", padx=10, pady=(10, 0))
            ttk.Label(w, text=self.t(f"set_{k}_h"), wraplength=420, foreground="#555", justify="left").grid(row=r + 1, column=1, sticky="w", padx=10)
            r += 2

        def ok():
            try:
                for k in ("budget", "ctx"):
                    if int(vars_[k].get()) <= 0:
                        raise ValueError
                if float(vars_["max_kb"].get()) <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(self.t("bad_value_title"), self.t("bad_value_msg"), parent=w)
                return
            for k, v in vars_.items():
                val = str(int(v.get())) if k in ("budget", "ctx") else v.get().strip()
                core.set_setting(self.conn, k, val)
                self.st[k] = val
            old_lang = self.lang
            for key, cb in (("lang", cb_l), ("prompt_lang", cb_p)):
                core.set_setting(self.conn, key, codes[cb.current()])
                self.st[key] = codes[cb.current()]
            self.lang = i18n.resolve(self.st["lang"])
            w.destroy()
            if self.lang != old_lang:
                self.rebuild_ui()
            elif self.cur_file:
                self.make_prompts()

        bar = ttk.Frame(w)
        bar.grid(row=r, column=0, columnspan=2, sticky="e", padx=10, pady=12)
        ttk.Button(bar, text=self.t("cancel"), command=w.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bar, text=self.t("save"), command=ok).pack(side="right")

    # ---------------- kılavuz ----------------
    def show_guide(self, lang=None):
        if self.guide_win is not None:
            try:
                if self.guide_win.winfo_exists():
                    self.guide_win.lift()
                    return
            except Exception:  # kd-ignore (pencere zaten kapanmış)
                pass
        w = tk.Toplevel(self)
        self.guide_win = w
        w.geometry("920x720")
        bar = ttk.Frame(w)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Label(bar, text=self.t("g_view")).pack(side="left")
        fr = ttk.Frame(w)
        fr.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        txt = tk.Text(fr, wrap="word", font=("Segoe UI", 10), padx=12, pady=8, bg="#ffffff")
        sb = ttk.Scrollbar(fr, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.tag_configure("h1", font=("Segoe UI", 17, "bold"), foreground="#1e3a8a", spacing1=6, spacing3=8)
        txt.tag_configure("h2", font=("Segoe UI", 12, "bold"), foreground="#1e3a8a", spacing1=14, spacing3=4)
        txt.tag_configure("p", spacing3=4)
        txt.tag_configure("li", lmargin1=18, lmargin2=34, spacing3=2)
        txt.tag_configure("code", font=self.mono, background="#f1f5f9", lmargin1=18, lmargin2=18, spacing3=4)

        def render(code):
            w.title(i18n.t("g_title", code))
            txt.config(state="normal")
            txt.delete("1.0", "end")
            for kind, text in i18n.GUIDE[code]:
                if kind == "li":
                    txt.insert("end", "•  " + text + "\n", "li")
                else:
                    txt.insert("end", text + "\n", kind)
            txt.config(state="disabled")
            txt.yview_moveto(0)

        ttk.Button(bar, text="Türkçe", command=lambda: render("tr")).pack(side="left", padx=(8, 2))
        ttk.Button(bar, text="English", command=lambda: render("en")).pack(side="left", padx=2)
        ttk.Button(bar, text=self.t("g_close"), command=w.destroy).pack(side="right")
        render(lang or self.lang)

    # ---------------- geri bildirim ----------------
    def feedback_dialog(self):
        w = tk.Toplevel(self)
        w.title(self.t("fb_title"))
        w.geometry("760x780")
        w.transient(self)
        w.columnconfigure(1, weight=1)
        kinds = list(core.FEEDBACK_KINDS)
        sc = None
        if self.scan_id:
            sc = self.conn.execute("SELECT * FROM scans WHERE id=?", (self.scan_id,)).fetchone()

        ttk.Label(w, text=self.t("fb_kind")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        kc = ttk.Combobox(w, state="readonly", values=[self.t("fb_k_bug"), self.t("fb_k_idea"), self.t("fb_k_question")])
        kc.grid(row=0, column=1, sticky="we", padx=10, pady=(10, 4))
        kc.current(0)
        ttk.Label(w, text=self.t("fb_subject")).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        tv = tk.StringVar()
        ttk.Entry(w, textvariable=tv).grid(row=1, column=1, sticky="we", padx=10, pady=4)
        ttk.Label(w, text=self.t("fb_desc")).grid(row=2, column=0, sticky="nw", padx=10, pady=4)
        td = tk.Text(w, height=7, wrap="word")
        td.grid(row=2, column=1, sticky="we", padx=10, pady=4)
        ttk.Label(w, text=self.t("fb_steps")).grid(row=3, column=0, sticky="nw", padx=10, pady=4)
        ts = tk.Text(w, height=5, wrap="word")
        ts.grid(row=3, column=1, sticky="we", padx=10, pady=4)
        dv = tk.IntVar(value=1)
        ttk.Checkbutton(w, text=self.t("fb_diag"), variable=dv, command=lambda: refresh()).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=4)
        ttk.Label(w, text=self.t("fb_preview"), font=("Segoe UI", 10, "bold")).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
        pv = tk.Text(w, height=11, wrap="word", font=self.mono, state="disabled", bg="#fafafa")
        pv.grid(row=6, column=0, columnspan=2, sticky="nsew", padx=10)
        w.rowconfigure(6, weight=1)
        ttk.Label(w, text=self.t("fb_privacy"), wraplength=700, foreground="#555", justify="left").grid(
            row=7, column=0, columnspan=2, sticky="w", padx=10, pady=8)

        def compose():
            kind = kinds[max(kc.current(), 0)]
            return kind, core.feedback_text(kind, tv.get(), td.get("1.0", "end"), ts.get("1.0", "end"), bool(dv.get()), self.lang, sc)

        def refresh(_e=None):
            _, (t, b) = compose()
            self._set_text(pv, f"{t}\n\n{b}")

        for widget in (td, ts):
            widget.bind("<KeyRelease>", refresh)
        kc.bind("<<ComboboxSelected>>", refresh)
        tv.trace_add("write", lambda *_: refresh())

        def valid():
            if not tv.get().strip() or not td.get("1.0", "end").strip():
                messagebox.showwarning(self.t("fb_title"), self.t("fb_empty"), parent=w)
                return False
            return True

        def open_gh():
            if not valid():
                return
            kind, (t, b) = compose()
            url, truncated = core.feedback_url(kind, t, b, self.lang)
            if truncated:
                self.clipboard_clear()
                self.clipboard_append(f"{t}\n\n{b}")
                messagebox.showinfo(self.t("fb_title"), self.t("fb_long"), parent=w)
            webbrowser.open(url)

        def copy():
            if not valid():
                return
            _, (t, b) = compose()
            self.clipboard_clear()
            self.clipboard_append(f"{t}\n\n{b}")
            self.status.set(self.t("fb_copied"))

        def save():
            if not valid():
                return
            _, (t, b) = compose()
            p = filedialog.asksaveasfilename(defaultextension=".md", initialfile="feedback.md", parent=w,
                                             filetypes=[("Markdown", "*.md"), (self.t("ft_text"), "*.txt")])
            if p:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(f"{t}\n\n{b}")
                self.status.set(self.t("fb_saved", p=p))

        bar = ttk.Frame(w)
        bar.grid(row=8, column=0, columnspan=2, sticky="e", padx=10, pady=(0, 12))
        ttk.Button(bar, text=self.t("g_close"), command=w.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bar, text=self.t("fb_save"), command=save).pack(side="right", padx=(6, 0))
        ttk.Button(bar, text=self.t("fb_copy"), command=copy).pack(side="right", padx=(6, 0))
        ttk.Button(bar, text=self.t("fb_open"), style="Big.TButton", command=open_gh).pack(side="right")
        refresh()

    def about(self):
        messagebox.showinfo(self.t("m_about"), self.t("about_body", name=i18n.APP_NAME[self.lang], ver=core.APP_VER,
                                                        data=core.data_dir(), url=core.REPO_URL))

    def _close(self):
        self.cancel.set()
        try:
            self.conn.close()
        except Exception:  # kd-ignore (kapanışta hata önemsiz)
            pass
        self.destroy()


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # kd-ignore (eski Windows)
            pass
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KodDenetci.App")
        except Exception:  # kd-ignore (görev çubuğu kimliği isteğe bağlı)
            pass
    try:
        App().mainloop()
    except Exception:
        import traceback
        err = traceback.format_exc()
        try:
            with open(os.path.join(core.data_dir(), "hata.log"), "a", encoding="utf-8") as fh:
                fh.write(err + "\n")
        except OSError:
            pass
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Kod Denetçi / CodeAuditor", err[-1500:])
        except Exception:  # kd-ignore (arayüz hiç kurulamadı)
            print(err)


if __name__ == "__main__":
    main()
