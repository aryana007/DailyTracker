import os
import shutil
import difflib
import glob
import re
import ast
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


DEFAULT_DIR = r"C:\Users\dell\Desktop\DailyTracker"
DEFAULT_FILE = os.path.join(DEFAULT_DIR, "daily_tracker.py")

BG_APP = "#F4F6F9"
BG_CARD = "#FFFFFF"
FG_PRIMARY = "#1F2937"
FG_MUTED = "#6B7280"
ACCENT = "#1A73E8"
ACCENT_HOVER = "#1557B0"
BORDER = "#E5E7EB"


def adjust_relative_indent(block: str, target_indent: str) -> str:
    """Adjusts leading indentation of a block while preserving internal relative indents."""
    lines = block.splitlines(keepends=False)
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return block
    min_indent = min(len(ln) - len(ln.lstrip(" ")) for ln in non_empty)
    out = []
    for ln in lines:
        if ln.strip():
            out.append(target_indent + ln[min_indent:])
        else:
            out.append("")
    return "\n".join(out)


def parse_line_range(raw: str, max_lines: int):
    """Parses single line or range (e.g., '42', '10-25', '10:25', '10..25')."""
    raw = raw.strip()
    m = re.match(r"^(\d+)(?:\s*(?:-|:|\.\.)\s*(\d+))?$", raw)
    if not m:
        raise ValueError(
            f"Invalid Line Number or Range: {raw!r}. Use format like '42' or '42-50'."
        )
    s = int(m.group(1))
    e = int(m.group(2)) if m.group(2) else s
    if s < 1 or e < 1:
        raise ValueError("Line numbers must be positive integers starting from 1.")
    if s > e:
        raise ValueError(f"Start line ({s}) cannot be greater than end line ({e}).")
    if s > max_lines:
        raise IndexError(
            f"Start line {s} exceeds total lines in file ({max_lines})."
        )
    e = min(e, max_lines)
    return s - 1, e - 1


class CodePatcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python File Patcher Helper")
        self.root.geometry("820x840")
        self.root.minsize(700, 720)
        self.root.configure(bg=BG_APP)

        self.last_backup_path = None
        self._build_ui()
        self._load_file_info()

    def _card(self, parent, title):
        frame = tk.Frame(
            parent,
            bg=BG_CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        frame.pack(fill="x", pady=(0, 10))
        tk.Label(
            frame,
            text=title,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))
        return frame

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG_APP, padx=18, pady=12)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="Python File Patcher Helper",
            bg=BG_APP,
            fg=FG_PRIMARY,
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            hdr,
            text="Target a Python file on your PC, locate by line/keyword/snippet, preview diffs, and patch safely with backups",
            bg=BG_APP,
            fg=FG_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        main = tk.Frame(self.root, bg=BG_APP, padx=18)
        main.pack(fill="both", expand=True)

        # 1. Target File & Location
        file_card = self._card(main, "1. Target Python File & Location on Laptop")
        path_row = tk.Frame(file_card, bg=BG_CARD)
        path_row.pack(fill="x")

        self.file_var = tk.StringVar(
            value=DEFAULT_FILE if os.path.exists(DEFAULT_FILE) else ""
        )
        entry = tk.Entry(
            path_row,
            textvariable=self.file_var,
            font=("Consolas", 9),
            bg="#FAFAFA",
            fg=FG_PRIMARY,
            relief="solid",
            bd=1,
        )
        entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        entry.bind("<FocusOut>", lambda _e: self._load_file_info())

        tk.Button(
            path_row,
            text="Browse .py",
            command=self._browse_file,
            bg="#E5E7EB",
            fg=FG_PRIMARY,
            relief="flat",
            padx=10,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            path_row,
            text="Reload Info",
            command=self._load_file_info,
            bg="#EEF3FD",
            fg=ACCENT,
            relief="flat",
            padx=10,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left")

        self.file_meta_label = tk.Label(
            file_card,
            text="File status: checking...",
            bg=BG_CARD,
            fg=FG_MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.file_meta_label.pack(fill="x", pady=(6, 0))

        # 2. How to Find & What to Change
        patch_card = self._card(main, "2. Search Target & Change Action")

        opt_row = tk.Frame(patch_card, bg=BG_CARD)
        opt_row.pack(fill="x", pady=(0, 8))

        tk.Label(
            opt_row,
            text="Locate By:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        self.locate_mode = ttk.Combobox(
            opt_row,
            values=[
                "Exact Keyword / Snippet",
                "Line Number / Range",
                "End of File (Append)",
                "Start of File (Prepend)",
            ],
            state="readonly",
            width=24,
        )
        self.locate_mode.current(0)
        self.locate_mode.pack(side="left", padx=(6, 16))
        self.locate_mode.bind(
            "<<ComboboxSelected>>", lambda _e: self._toggle_search_inputs()
        )

        tk.Label(
            opt_row,
            text="Action:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")
        self.action_mode = ttk.Combobox(
            opt_row,
            values=[
                "Replace Match",
                "Insert After Match",
                "Insert Before Match",
                "Delete Matched Line(s) / Text",
                "Tabs -> 4 Spaces (Whole File)",
            ],
            state="readonly",
            width=26,
        )
        self.action_mode.current(0)
        self.action_mode.pack(side="left", padx=(6, 0))

        # Target options container (toggled dynamically based on locate mode)
        self.locator_row = tk.Frame(patch_card, bg=BG_CARD)
        self.locator_row.pack(fill="x", pady=(0, 8))

        # Line number widgets
        self.line_label = tk.Label(
            self.locator_row,
            text="Line / Range:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        )
        self.line_range_var = tk.StringVar(value="1")
        self.line_range_entry = tk.Entry(
            self.locator_row,
            textvariable=self.line_range_var,
            width=12,
            font=("Consolas", 9),
            bg="#FAFAFA",
        )
        self.line_hint_label = tk.Label(
            self.locator_row,
            text="(e.g. 42 or 42-55)",
            bg=BG_CARD,
            fg=FG_MUTED,
            font=("Segoe UI", 8),
        )

        # Keyword / Snippet options widgets
        self.scope_label = tk.Label(
            self.locator_row,
            text="Match Scope:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        )
        self.match_scope = ttk.Combobox(
            self.locator_row,
            values=["Exact Snippet / Text", "Entire Line(s) Containing Match"],
            state="readonly",
            width=23,
        )
        self.match_scope.current(0)

        self.occ_label = tk.Label(
            self.locator_row,
            text="Occurrence:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        )
        self.occurrence_mode = ttk.Combobox(
            self.locator_row,
            values=["Require Unique (1 match)", "First Match", "All Matches"],
            state="readonly",
            width=20,
        )
        self.occurrence_mode.current(0)

        self.case_sensitive_var = tk.BooleanVar(value=True)
        self.case_check = tk.Checkbutton(
            self.locator_row,
            text="Case-sensitive",
            variable=self.case_sensitive_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        )

        self.tolerate_ws_var = tk.BooleanVar(value=True)
        self.tolerate_ws_check = tk.Checkbutton(
            self.locator_row,
            text="Tolerate trailing spaces",
            variable=self.tolerate_ws_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        )

        # Search keyword / snippet box
        self.search_label = tk.Label(
            patch_card,
            text="Search Keyword / Exact Text to Find (for Keyword mode):",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.search_label.pack(fill="x")
        self.search_text = tk.Text(
            patch_card,
            height=3,
            font=("Consolas", 9),
            bg="#FAFAFA",
            fg=FG_PRIMARY,
            relief="solid",
            bd=1,
        )
        self.search_text.pack(fill="x", pady=(4, 8))

        # Replacement / insertion content box
        tk.Label(
            patch_card,
            text="New Code / Text to Replace With or Insert:",
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.replace_text = tk.Text(
            patch_card,
            height=5,
            font=("Consolas", 9),
            bg="#FAFAFA",
            fg=FG_PRIMARY,
            relief="solid",
            bd=1,
        )
        self.replace_text.pack(fill="x", pady=(4, 0))

        # 3. Important Safety & Formatting Options
        opts_card = self._card(main, "3. Important Options & Safety")
        row_a = tk.Frame(opts_card, bg=BG_CARD)
        row_a.pack(fill="x")

        self.backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row_a,
            text="Create timestamped .bak backup",
            variable=self.backup_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 14))

        self.auto_indent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            row_a,
            text="Match leading indent (preserves relative indent)",
            variable=self.auto_indent_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 14))

        self.convert_tabs_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row_a,
            text="Convert tabs to 4 spaces",
            variable=self.convert_tabs_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(0, 14))

        self.validate_syntax_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row_a,
            text="Validate Python syntax before apply",
            variable=self.validate_syntax_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            font=("Segoe UI", 9),
        ).pack(side="left")

        # Action Buttons
        btn_bar = tk.Frame(main, bg=BG_APP, pady=4)
        btn_bar.pack(fill="x")

        tk.Button(
            btn_bar,
            text="Preview Changes (Diff)",
            command=self.preview_diff,
            bg="#E5E7EB",
            fg=FG_PRIMARY,
            relief="flat",
            padx=12,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_bar,
            text="Validate Syntax",
            command=self.check_syntax_action,
            bg="#EEF3FD",
            fg=ACCENT,
            relief="flat",
            padx=12,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_bar,
            text="Apply Changes to File",
            command=self.apply_changes,
            bg=ACCENT,
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(0, 8))

        self.undo_btn = tk.Button(
            btn_bar,
            text="Restore Last .bak",
            command=self.restore_backup,
            bg="#FEF3C7",
            fg="#92400E",
            relief="flat",
            padx=12,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            state="disabled",
        )
        self.undo_btn.pack(side="right")

        # 4. Diff / Log Output
        out_card = self._card(main, "4. Diff Preview & Execution Log")
        self.output_text = tk.Text(
            out_card,
            height=10,
            font=("Consolas", 9),
            bg="#111827",
            fg="#E5E7EB",
            relief="flat",
            bd=6,
        )
        self.output_text.pack(fill="both", expand=True)

        # Configure color tags for unified diff and log messages
        self.output_text.tag_configure("diff_add", foreground="#34D399")     # emerald
        self.output_text.tag_configure("diff_del", foreground="#F87171")     # rose red
        self.output_text.tag_configure("diff_hunk", foreground="#60A5FA")    # light blue
        self.output_text.tag_configure("diff_hdr", foreground="#9CA3AF")     # muted gray
        self.output_text.tag_configure("log_info", foreground="#E5E7EB")     # light
        self.output_text.tag_configure("log_success", foreground="#34D399")  # green
        self.output_text.tag_configure("log_warn", foreground="#FBBF24")     # yellow
        self.output_text.tag_configure("log_err", foreground="#F87171")      # red

        self._toggle_search_inputs()

    def _toggle_search_inputs(self):
        mode = self.locate_mode.get()
        # Clear locator row widgets
        for w in self.locator_row.winfo_children():
            w.pack_forget()

        if mode == "Line Number / Range":
            self.line_label.pack(side="left")
            self.line_range_entry.pack(side="left", padx=(6, 6))
            self.line_hint_label.pack(side="left", padx=(0, 16))
            self.search_label.config(state="disabled")
            self.search_text.config(state="disabled", bg="#E5E7EB")
        elif mode == "Exact Keyword / Snippet":
            self.scope_label.pack(side="left")
            self.match_scope.pack(side="left", padx=(6, 12))
            self.occ_label.pack(side="left")
            self.occurrence_mode.pack(side="left", padx=(6, 12))
            self.case_check.pack(side="left", padx=(0, 10))
            self.tolerate_ws_check.pack(side="left")
            self.search_label.config(state="normal")
            self.search_text.config(state="normal", bg="#FAFAFA")
        else:
            self.search_label.config(state="disabled")
            self.search_text.config(state="disabled", bg="#E5E7EB")

    def _browse_file(self):
        start_dir = DEFAULT_DIR if os.path.isdir(DEFAULT_DIR) else os.getcwd()
        path = filedialog.askopenfilename(
            initialdir=start_dir,
            title="Select Python File to Edit",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            self._load_file_info()

    def _load_file_info(self):
        path = self.file_var.get().strip()
        if not path or not os.path.exists(path):
            self.file_meta_label.config(
                text="File status: Not found — check path or click Browse .py.",
                fg="#DC2626",
            )
            self.undo_btn.config(state="disabled", text="Restore Last .bak")
            return

        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            line_count = len(lines)
        size_kb = os.path.getsize(path) / 1024

        # Check for backups
        bak_pattern = f"{path}.*.bak"
        baks = sorted(glob.glob(bak_pattern), key=os.path.getmtime, reverse=True)
        if baks:
            self.last_backup_path = baks[0]
            bak_name = os.path.basename(self.last_backup_path)
            self.undo_btn.config(
                state="normal",
                text=f"Restore Last .bak ({bak_name[:20]}...)" if len(bak_name) > 23 else f"Restore Last .bak ({bak_name})"
            )
            bak_info = f"  |  Found {len(baks)} backup(s)"
        else:
            self.undo_btn.config(state="disabled", text="Restore Last .bak")
            bak_info = ""

        self.file_meta_label.config(
            text=f"File found: {os.path.abspath(path)}  |  {line_count} lines  |  {size_kb:.1f} KB{bak_info}",
            fg="#059669",
        )

    def _log(self, msg: str, tag: str = "log_info", clear: bool = False):
        if clear:
            self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, msg + "\n", tag)
        self.output_text.see(tk.END)

    def _compute_updated_content(self, original: str) -> str:
        action = self.action_mode.get()
        locate = self.locate_mode.get()
        new_block = self.replace_text.get("1.0", tk.END)
        if new_block.endswith("\n"):
            new_block = new_block[:-1]

        has_crlf = "\r\n" in original
        native_nl = "\r\n" if has_crlf else "\n"

        orig_norm = original.replace("\r\n", "\n")
        new_norm = new_block.replace("\r\n", "\n")

        if self.convert_tabs_var.get():
            orig_norm = orig_norm.replace("\t", "    ")
            new_norm = new_norm.replace("\t", "    ")

        if action == "Tabs -> 4 Spaces (Whole File)":
            return orig_norm.replace("\n", native_nl)

        if locate == "End of File (Append)":
            sep = "" if orig_norm.endswith("\n") or not orig_norm else "\n"
            res = orig_norm + sep + new_norm + ("\n" if new_norm and not new_norm.endswith("\n") else "")
            return res.replace("\n", native_nl)

        if locate == "Start of File (Prepend)":
            suffix = "\n" if new_norm and not new_norm.endswith("\n") else ""
            res = new_norm + suffix + orig_norm
            return res.replace("\n", native_nl)

        lines = orig_norm.splitlines(keepends=True)

        if locate == "Line Number / Range":
            s_idx, e_idx = parse_line_range(self.line_range_var.get(), len(lines))
            target_line = lines[s_idx]
            leading_ws = target_line[: len(target_line) - len(target_line.lstrip(" "))]

            block_to_insert = new_norm
            if self.auto_indent_var.get() and block_to_insert:
                block_to_insert = adjust_relative_indent(block_to_insert, leading_ws)

            if not block_to_insert.endswith("\n") and block_to_insert:
                block_to_insert += "\n"

            if action == "Replace Match":
                lines[s_idx : e_idx + 1] = [block_to_insert]
            elif action == "Insert After Match":
                lines.insert(e_idx + 1, block_to_insert)
            elif action == "Insert Before Match":
                lines.insert(s_idx, block_to_insert)
            elif action.startswith("Delete"):
                del lines[s_idx : e_idx + 1]

            return "".join(lines).replace("\n", native_nl)

        # Locate by Exact Keyword / Snippet
        needle_raw = self.search_text.get("1.0", tk.END)
        needle_norm = needle_raw.replace("\r\n", "\n")
        if needle_norm.endswith("\n"):
            needle_norm = needle_norm[:-1]
        if not needle_norm:
            raise ValueError("Please enter a Search Keyword / Exact Text to find.")

        case_sens = self.case_sensitive_var.get()
        hay = orig_norm if case_sens else orig_norm.lower()
        tgt = needle_norm if case_sens else needle_norm.lower()

        matches = []
        if tgt in hay:
            start = 0
            t_len = max(1, len(tgt))
            while True:
                idx = hay.find(tgt, start)
                if idx == -1:
                    break
                matches.append((idx, idx + len(tgt)))
                start = idx + t_len
        elif self.tolerate_ws_var.get():
            # Line-by-line whitespace-tolerant fallback
            orig_lines = orig_norm.splitlines(keepends=True)
            needle_lines = needle_norm.splitlines(keepends=False)
            m = len(needle_lines)
            if m > 0:
                char_pos = 0
                line_starts = []
                for ln in orig_lines:
                    line_starts.append(char_pos)
                    char_pos += len(ln)
                line_starts.append(char_pos)
                for i in range(len(orig_lines) - m + 1):
                    matched = True
                    for k in range(m):
                        ol = orig_lines[i + k].rstrip("\r\n").rstrip(" ")
                        nl = needle_lines[k].rstrip(" ")
                        if not case_sens:
                            ol, nl = ol.lower(), nl.lower()
                        if ol != nl:
                            matched = False
                            break
                    if matched:
                        matches.append((line_starts[i], line_starts[i + m]))

        if not matches:
            raise LookupError(f"Search target was not found: {needle_norm[:40]!r}")

        occ = self.occurrence_mode.get()
        if occ == "Require Unique (1 match)" and len(matches) > 1:
            raise LookupError(
                f"Found {len(matches)} matches. Select 'First Match' or 'All Matches', or provide a more specific search snippet."
            )
        if occ == "First Match":
            matches = [matches[0]]

        scope = self.match_scope.get()
        if scope == "Entire Line(s) Containing Match":
            expanded = []
            for s, e in matches:
                line_start = orig_norm.rfind("\n", 0, s)
                line_start = 0 if line_start == -1 else line_start + 1
                line_end = orig_norm.find("\n", e)
                line_end = len(orig_norm) if line_end == -1 else line_end + 1
                expanded.append((line_start, line_end))
            matches = expanded

        out_chars = list(orig_norm)
        for s, e in sorted(matches, key=lambda x: x[0], reverse=True):
            line_start = orig_norm.rfind("\n", 0, s)
            line_start = 0 if line_start == -1 else line_start + 1
            full_line = orig_norm[
                line_start : orig_norm.find("\n", line_start)
                if orig_norm.find("\n", line_start) != -1
                else len(orig_norm)
            ]
            leading_ws = full_line[: len(full_line) - len(full_line.lstrip(" "))]

            block_to_insert = new_norm
            if self.auto_indent_var.get() and block_to_insert:
                if scope == "Entire Line(s) Containing Match" or "\n" in block_to_insert:
                    block_to_insert = adjust_relative_indent(block_to_insert, leading_ws)

            if action == "Replace Match":
                if scope == "Entire Line(s) Containing Match" and block_to_insert and not block_to_insert.endswith("\n"):
                    block_to_insert += "\n"
                out_chars[s:e] = list(block_to_insert)
            elif action == "Insert After Match":
                ins = block_to_insert
                if scope == "Entire Line(s) Containing Match" and not ins.endswith("\n"):
                    ins += "\n"
                out_chars[e:e] = list(ins)
            elif action == "Insert Before Match":
                ins = block_to_insert
                if scope == "Entire Line(s) Containing Match" and not ins.endswith("\n"):
                    ins += "\n"
                out_chars[s:s] = list(ins)
            elif action.startswith("Delete"):
                out_chars[s:e] = []

        return "".join(out_chars).replace("\n", native_nl)

    def _validate_syntax(self, code: str):
        try:
            ast.parse(code)
            return True, "Python syntax is valid."
        except SyntaxError as err:
            return False, f"SyntaxError at line {err.lineno}, col {err.offset}: {err.msg}"
        except Exception as exc:
            return False, f"Syntax verification error: {exc}"

    def check_syntax_action(self):
        path = self.file_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("File Missing", "Select a valid Python file first.")
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            valid, msg = self._validate_syntax(content)
            if valid:
                self._log(f"Current File ({os.path.basename(path)}): {msg}", tag="log_success", clear=True)
                messagebox.showinfo("Syntax Valid", f"No syntax errors in {os.path.basename(path)}.")
            else:
                self._log(f"Current File ({os.path.basename(path)}): {msg}", tag="log_err", clear=True)
                messagebox.showwarning("Syntax Error", msg)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def preview_diff(self):
        path = self.file_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("File Missing", "Select a valid Python file first.")
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                original = f.read()
            updated = self._compute_updated_content(original)
            diff_lines = list(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    updated.splitlines(keepends=True),
                    fromfile=f"a/{os.path.basename(path)}",
                    tofile=f"b/{os.path.basename(path)}",
                    n=2,
                )
            )

            self.output_text.delete("1.0", tk.END)

            # Check syntax if python file
            if path.endswith(".py") and self.validate_syntax_var.get():
                valid, syn_msg = self._validate_syntax(updated)
                if valid:
                    self._log(f"[Python Syntax Check] OK: {syn_msg}\n", tag="log_success")
                else:
                    self._log(f"[Python Syntax Warning] {syn_msg}\n", tag="log_warn")

            if not diff_lines:
                self._log("No differences detected between original and updated content.", tag="log_info")
            else:
                for line in diff_lines:
                    if line.startswith("+++") or line.startswith("---"):
                        self.output_text.insert(tk.END, line, "diff_hdr")
                    elif line.startswith("+"):
                        self.output_text.insert(tk.END, line, "diff_add")
                    elif line.startswith("-"):
                        self.output_text.insert(tk.END, line, "diff_del")
                    elif line.startswith("@@"):
                        self.output_text.insert(tk.END, line, "diff_hunk")
                    else:
                        self.output_text.insert(tk.END, line, "diff_hdr")
                self.output_text.see(tk.END)

        except Exception as exc:
            messagebox.showerror("Preview Error", str(exc))

    def apply_changes(self):
        path = self.file_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showerror("File Missing", "Select a valid Python file first.")
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                original = f.read()
            updated = self._compute_updated_content(original)

            # Safety syntax check
            if path.endswith(".py") and self.validate_syntax_var.get():
                valid, syn_msg = self._validate_syntax(updated)
                if not valid:
                    proceed = messagebox.askyesno(
                        "Python Syntax Warning",
                        f"The patched content contains a syntax error:\n\n{syn_msg}\n\nDo you still want to apply changes?",
                    )
                    if not proceed:
                        self._log(f"Aborted apply due to syntax error: {syn_msg}", tag="log_err", clear=True)
                        return

            if self.backup_var.get():
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak_path = f"{path}.{stamp}.bak"
                shutil.copy2(path, bak_path)
                self.last_backup_path = bak_path

            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(updated)

            self._load_file_info()
            msg = f"Updated: {os.path.abspath(path)}"
            if self.last_backup_path and self.backup_var.get():
                msg += f"\nBackup saved: {self.last_backup_path}"
            self._log(msg, tag="log_success", clear=True)
            messagebox.showinfo("Changes Applied", msg)
        except Exception as exc:
            messagebox.showerror("Apply Failed", str(exc))

    def restore_backup(self):
        path = self.file_var.get().strip()
        if not self.last_backup_path or not os.path.exists(self.last_backup_path):
            messagebox.showwarning("No Backup", "No recent .bak file available to restore.")
            return
        bak_name = os.path.basename(self.last_backup_path)
        confirm = messagebox.askyesno(
            "Confirm Restore",
            f"Restore backup:\n{bak_name}\n\nThis will overwrite current {os.path.basename(path)}. Proceed?",
        )
        if not confirm:
            return

        shutil.copy2(self.last_backup_path, path)
        self._load_file_info()
        self._log(f"Restored {path} from {self.last_backup_path}", tag="log_success", clear=True)
        messagebox.showinfo("Restored", f"Successfully restored from {bak_name}.")


if __name__ == "__main__":
    root = tk.Tk()
    app = CodePatcherApp(root)
    root.mainloop()
