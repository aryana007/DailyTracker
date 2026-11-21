import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import threading
import os
import json
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from PIL import Image, ImageTk

# Configuration & Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_QUEUE_FILE = os.path.join(BASE_DIR, "pending_logs.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.png")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
SHEET_NAME = "Daily Routine & Food Log"

HEADERS = [
    "Date",
    "Wake Up Time",
    "Running Time (mins)",
    "Walk Time (mins)",
    "Total Office Time (hrs)",
    "Meals Count",
    "Food Details",
    "Synced At",
]

THEMES = {
    "light": {
        "app_bg": "#F8FAFC",
        "card_bg": "#FFFFFF",
        "card_border": "#E2E8F0",
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "accent": "#2563EB",
        "accent_hover": "#1D4ED8",
        "accent_light": "#EFF6FF",
        "chip_bg": "#F1F5F9",
        "chip_hover": "#E2E8F0",
        "chip_fg": "#334155",
        "chip_accent_fg": "#2563EB",
        "input_bg": "#FAFAFA",
        "input_border": "#CBD5E1",
        "btn_sec_bg": "#F1F5F9",
        "btn_sec_hover": "#E2E8F0",
        "btn_sec_fg": "#1E293B",
        "kpi_bg": "#FFFFFF",
        "kpi_border": "#E2E8F0",
        "kpi_num": "#0F172A",
        "kpi_label": "#64748B",
        "status_ok": "#059669",
        "status_warn": "#D97706",
        "status_err": "#DC2626",
        "toast_bg": "#0F172A",
        "toast_fg": "#F8FAFC",
    },
    "dark": {
        "app_bg": "#0F172A",
        "card_bg": "#1E293B",
        "card_border": "#334155",
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "accent": "#38BDF8",
        "accent_hover": "#0EA5E9",
        "accent_light": "#082F49",
        "chip_bg": "#334155",
        "chip_hover": "#475569",
        "chip_fg": "#E2E8F0",
        "chip_accent_fg": "#38BDF8",
        "input_bg": "#0F172A",
        "input_border": "#475569",
        "btn_sec_bg": "#334155",
        "btn_sec_hover": "#475569",
        "btn_sec_fg": "#F8FAFC",
        "kpi_bg": "#1E293B",
        "kpi_border": "#334155",
        "kpi_num": "#38BDF8",
        "kpi_label": "#94A3B8",
        "status_ok": "#34D399",
        "status_warn": "#FBBF24",
        "status_err": "#F87171",
        "toast_bg": "#1E293B",
        "toast_fg": "#F8FAFC",
    },
}


def get_google_sheet():
    """Authenticates user via OAuth and opens/creates the target Google Sheet."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "Missing 'credentials.json'. Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    client = gspread.authorize(creds)

    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.sheet1
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SHEET_NAME)
        worksheet = spreadsheet.sheet1
        worksheet.append_row(HEADERS)

    if not worksheet.row_values(1):
        worksheet.append_row(HEADERS)

    return worksheet


class ModernButton(tk.Canvas):
    """Custom flat rounded button with smooth hover feedback and disabled state."""

    def __init__(
        self,
        parent,
        text,
        command,
        bg="#2563EB",
        hover_bg="#1D4ED8",
        fg="#FFFFFF",
        width=180,
        height=38,
        bold=True,
        radius=8,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.command = command
        self.bg_normal = bg
        self.bg_hover = hover_bg
        self.bg_disabled = "#94A3B8"
        self.fg_normal = fg
        self.text = text
        self.width = width
        self.height = height
        self.radius = radius
        self.enabled = True
        self.font = ("Segoe UI", 10, "bold" if bold else "normal")

        self.poly_id = self._draw_rounded_rect(
            2, 2, width - 2, height - 2, radius, fill=self.bg_normal, outline=""
        )
        self.text_id = self.create_text(
            width // 2, height // 2, text=self.text, fill=self.fg_normal, font=self.font
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, _event=None):
        if self.enabled:
            self.itemconfig(self.poly_id, fill=self.bg_hover)

    def _on_leave(self, _event=None):
        if self.enabled:
            self.itemconfig(self.poly_id, fill=self.bg_normal)

    def _on_click(self, _event=None):
        if self.enabled and callable(self.command):
            self.command()

    def set_enabled(self, state: bool):
        self.enabled = state
        self.config(cursor="hand2" if state else "arrow")
        self.itemconfig(
            self.poly_id, fill=self.bg_normal if state else self.bg_disabled
        )

    def update_style(self, bg_normal, bg_hover, fg_normal, parent_bg):
        self.bg_normal = bg_normal
        self.bg_hover = bg_hover
        self.fg_normal = fg_normal
        self.config(bg=parent_bg)
        self.itemconfig(
            self.poly_id, fill=self.bg_normal if self.enabled else self.bg_disabled
        )
        self.itemconfig(self.text_id, fill=self.fg_normal)


class DailyTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Daily Routine & Food Logger")
        self.root.geometry("580x830")
        self.root.minsize(530, 720)

        self.theme_name = "light"
        self.entries = {}
        self.cards = []
        self.sub_labels = []
        self.chips = []
        self.buttons = []
        self.is_syncing = False
        self.logo_img = None
        self.toast_job = None

        self._build_ui()
        self._bind_shortcuts()
        self.update_queue_status()
        self.update_kpi_summary()

    @property
    def colors(self):
        return THEMES[self.theme_name]

    def _create_card(self, parent, eyebrow=None, title=None):
        card = tk.Frame(
            parent,
            bg=self.colors["card_bg"],
            highlightbackground=self.colors["card_border"],
            highlightthickness=1,
            padx=18,
            pady=12,
        )
        card.pack(fill="x", pady=(0, 10))
        self.cards.append(card)

        if eyebrow or title:
            header_box = tk.Frame(card, bg=self.colors["card_bg"])
            header_box.pack(fill="x", pady=(0, 6))
            self.cards.append(header_box)

            if eyebrow:
                lbl_eyebrow = tk.Label(
                    header_box,
                    text=eyebrow.upper(),
                    bg=self.colors["card_bg"],
                    fg=self.colors["text_secondary"],
                    font=("Segoe UI", 8, "bold"),
                    anchor="w",
                )
                lbl_eyebrow.pack(fill="x")
                self.sub_labels.append(lbl_eyebrow)

            if title:
                lbl_title = tk.Label(
                    header_box,
                    text=title,
                    bg=self.colors["card_bg"],
                    fg=self.colors["text_primary"],
                    font=("Segoe UI", 11, "bold"),
                    anchor="w",
                )
                lbl_title.pack(fill="x")
                self.sub_labels.append(lbl_title)

        return card

    def _build_ui(self):
        self.root.configure(bg=self.colors["app_bg"])

        # Top Header
        self.header_frame = tk.Frame(self.root, bg=self.colors["app_bg"], padx=20, pady=12)
        self.header_frame.pack(fill="x")

        title_row = tk.Frame(self.header_frame, bg=self.colors["app_bg"])
        title_row.pack(fill="x")

        # Logo loading
        if os.path.exists(LOGO_FILE):
            pil_logo = Image.open(LOGO_FILE).resize(
                (42, 42), Image.Resampling.LANCZOS
            )
            self.logo_img = ImageTk.PhotoImage(pil_logo)
            self.root.iconphoto(False, self.logo_img)
            self.logo_label = tk.Label(
                title_row,
                image=self.logo_img,
                bg=self.colors["app_bg"],
            )
            self.logo_label.pack(side="left", padx=(0, 10))

        title_text_box = tk.Frame(title_row, bg=self.colors["app_bg"])
        title_text_box.pack(side="left")

        self.title_label = tk.Label(
            title_text_box,
            text="Daily Routine & Food Log",
            bg=self.colors["app_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.sub_header = tk.Label(
            title_text_box,
            text="Log habits, track metrics, and sync to Google Sheets",
            bg=self.colors["app_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.sub_header.pack(anchor="w")

        # Header Right Controls (Theme toggle & Help)
        hdr_right = tk.Frame(title_row, bg=self.colors["app_bg"])
        hdr_right.pack(side="right")

        self.theme_btn = tk.Button(
            hdr_right,
            text="🌙 Dark",
            command=self.toggle_theme,
            bg=self.colors["chip_bg"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["chip_hover"],
            activeforeground=self.colors["text_primary"],
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.theme_btn.pack(side="left", padx=(0, 6))

        self.help_btn = tk.Button(
            hdr_right,
            text="Help & Guide",
            command=self.open_help_guide,
            bg=self.colors["chip_bg"],
            fg=self.colors["accent"],
            activebackground=self.colors["chip_hover"],
            activeforeground=self.colors["accent_hover"],
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        self.help_btn.pack(side="left")

        # Main Container
        self.main_frame = tk.Frame(self.root, bg=self.colors["app_bg"], padx=20)
        self.main_frame.pack(fill="both", expand=True)

        # KPI Summary Strip (Live Daily Glance)
        self.kpi_card = tk.Frame(
            self.main_frame,
            bg=self.colors["kpi_bg"],
            highlightbackground=self.colors["kpi_border"],
            highlightthickness=1,
            padx=12,
            pady=8,
        )
        self.kpi_card.pack(fill="x", pady=(0, 10))
        self.cards.append(self.kpi_card)

        kpi_grid = tk.Frame(self.kpi_card, bg=self.colors["kpi_bg"])
        kpi_grid.pack(fill="x")
        self.cards.append(kpi_grid)

        self.kpi_move_val = tk.Label(
            kpi_grid,
            text="🏃 0m Active",
            bg=self.colors["kpi_bg"],
            fg=self.colors["accent"],
            font=("Segoe UI", 10, "bold"),
        )
        self.kpi_move_val.pack(side="left", expand=True)

        tk.Label(
            kpi_grid,
            text="|",
            bg=self.colors["kpi_bg"],
            fg=self.colors["card_border"],
        ).pack(side="left")

        self.kpi_office_val = tk.Label(
            kpi_grid,
            text="💼 0.0h Office",
            bg=self.colors["kpi_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10, "bold"),
        )
        self.kpi_office_val.pack(side="left", expand=True)

        tk.Label(
            kpi_grid,
            text="|",
            bg=self.colors["kpi_bg"],
            fg=self.colors["card_border"],
        ).pack(side="left")

        self.kpi_meals_val = tk.Label(
            kpi_grid,
            text="🍽️ 0 Meals",
            bg=self.colors["kpi_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 10, "bold"),
        )
        self.kpi_meals_val.pack(side="left", expand=True)

        # Card 1: Routine & Activity
        routine_card = self._create_card(
            self.main_frame, eyebrow="Daily Metrics", title="Routine & Movement"
        )

        # Date Navigator Row (< Today >)
        self._add_date_navigator(routine_card)

        # Wake Up Row with Quick Presets
        self._add_wake_up_row(routine_card)

        # Numeric Stepper Rows
        self._add_stepper_row(
            routine_card,
            icon="🏃",
            label="Running Time (mins)",
            key="run_time",
            default="0",
            step=5,
            presets=[("+15m", 15), ("+30m", 30), ("Clear", 0)],
            is_float=False,
        )
        self._add_stepper_row(
            routine_card,
            icon="🚶",
            label="Walk Time (mins)",
            key="walk_time",
            default="0",
            step=10,
            presets=[("+15m", 15), ("+30m", 30), ("Clear", 0)],
            is_float=False,
        )
        self._add_stepper_row(
            routine_card,
            icon="💼",
            label="Total Office Time (hrs)",
            key="office_time",
            default="0",
            step=0.5,
            presets=[("+1h", 1.0), ("+4h", 4.0), ("8h", 8.0), ("Clear", 0)],
            is_float=True,
        )

        # Card 2: Meals & Food
        food_card = self._create_card(
            self.main_frame, eyebrow="Nutrition", title="Food & Meals Log"
        )

        self._add_stepper_row(
            food_card,
            icon="🍽️",
            label="Times Food Eaten",
            key="meal_count",
            default="0",
            step=1,
            presets=[("+1", 1), ("Clear", 0)],
            is_float=False,
        )

        lbl_food_desc = tk.Label(
            food_card,
            text="What You Ate (Click quick chips or type details)",
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        )
        lbl_food_desc.pack(fill="x", pady=(8, 4))
        self.sub_labels.append(lbl_food_desc)

        # Quick-insert chips arranged in 2 rows to prevent right-edge clipping
        chips_outer = tk.Frame(food_card, bg=self.colors["card_bg"])
        chips_outer.pack(fill="x", pady=(0, 6))
        self.cards.append(chips_outer)

        chips_row1 = tk.Frame(chips_outer, bg=self.colors["card_bg"])
        chips_row1.pack(fill="x")
        self.cards.append(chips_row1)

        chips_row2 = tk.Frame(chips_outer, bg=self.colors["card_bg"])
        chips_row2.pack(fill="x", pady=(3, 0))
        self.cards.append(chips_row2)

        quick_meals = [
            ("🥣 Granola & Milk", "Granola & Milk"),
            ("🍛 Rice & Dal", "Rice & Dal"),
            ("🫓 Roti & Sabzi", "Roti & Sabzi"),
            ("☕ Tea / Coffee", "Tea / Coffee"),
            ("🍎 Fruit / Snack", "Fruit / Snack"),
            ("🥗 Salad / Greens", "Salad / Greens"),
        ]
        for idx, (label_text, meal_name) in enumerate(quick_meals):
            target_row = chips_row1 if idx < 3 else chips_row2
            btn = tk.Button(
                target_row,
                text=f"+ {label_text}",
                command=lambda m=meal_name: self._append_meal_chip(m),
                bg=self.colors["chip_bg"],
                fg=self.colors["chip_accent_fg"],
                activebackground=self.colors["chip_hover"],
                activeforeground=self.colors["accent_hover"],
                relief="flat",
                bd=0,
                padx=8,
                pady=3,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
            )
            btn.pack(side="left", padx=(0, 6), pady=1)
            self.chips.append(btn)

        self.text_container = tk.Frame(
            food_card,
            bg=self.colors["input_border"],
            padx=1,
            pady=1,
        )
        self.text_container.pack(fill="x", pady=(4, 0))

        self.food_text = tk.Text(
            self.text_container,
            height=3,
            font=("Segoe UI", 10),
            bg=self.colors["input_bg"],
            fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"],
            relief="flat",
            bd=6,
            wrap="word",
        )
        self.food_text.pack(fill="both", expand=True)

        # Card 3: Actions & Sync Status
        action_card = self._create_card(self.main_frame)

        btn_row = tk.Frame(action_card, bg=self.colors["card_bg"])
        btn_row.pack(fill="x")
        self.cards.append(btn_row)

        self.save_btn = ModernButton(
            btn_row,
            text="Save Locally (Ctrl+S)",
            command=self.save_locally,
            bg=self.colors["btn_sec_bg"],
            hover_bg=self.colors["btn_sec_hover"],
            fg=self.colors["btn_sec_fg"],
            width=210,
            height=40,
            bold=False,
            radius=8,
        )
        self.save_btn.pack(side="left")
        self.buttons.append((self.save_btn, "sec"))

        self.sync_btn = ModernButton(
            btn_row,
            text="Sync to Google Sheets",
            command=self.sync_to_google,
            bg=self.colors["accent"],
            hover_bg=self.colors["accent_hover"],
            fg="#FFFFFF",
            width=260,
            height=40,
            bold=True,
            radius=8,
        )
        self.sync_btn.pack(side="right")
        self.buttons.append((self.sync_btn, "prim"))

        # Status strip
        status_row = tk.Frame(action_card, bg=self.colors["card_bg"])
        status_row.pack(fill="x", pady=(10, 0))
        self.cards.append(status_row)

        self.queue_label = tk.Label(
            status_row,
            text="🟢 Local Queue: All synced",
            bg=self.colors["card_bg"],
            fg=self.colors["text_secondary"],
            font=("Segoe UI", 9),
        )
        self.queue_label.pack(side="left")

        self.status_label = tk.Label(
            status_row,
            text="Ready",
            bg=self.colors["card_bg"],
            fg=self.colors["status_ok"],
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="right")

        # Toast notification floating overlay
        self.toast_frame = tk.Frame(
            self.root,
            bg=self.colors["toast_bg"],
            padx=16,
            pady=8,
            highlightbackground="#64748B",
            highlightthickness=1,
            cursor="hand2",
        )
        self.toast_label = tk.Label(
            self.toast_frame,
            text="",
            bg=self.colors["toast_bg"],
            fg=self.colors["toast_fg"],
            font=("Segoe UI", 9, "bold"),
        )
        self.toast_label.pack()
        self.toast_frame.bind("<Button-1>", lambda _e: self._hide_toast())
        self.toast_label.bind("<Button-1>", lambda _e: self._hide_toast())

    def _show_toast(self, message: str, is_error: bool = False):
        if self.toast_job:
            self.root.after_cancel(self.toast_job)
            self.toast_job = None

        bg_color = self.colors["status_err"] if is_error else self.colors["toast_bg"]
        fg_color = "#FFFFFF" if is_error else self.colors["toast_fg"]
        self.toast_frame.config(bg=bg_color)
        self.toast_label.config(text=message, bg=bg_color, fg=fg_color)
        self.toast_frame.place(relx=0.5, rely=0.95, anchor="s")

        self.toast_job = self.root.after(3200, self._hide_toast)

    def _hide_toast(self):
        self.toast_frame.place_forget()
        self.toast_job = None

    def toggle_theme(self):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        c = self.colors
        self.theme_btn.config(text="☀️ Light" if self.theme_name == "dark" else "🌙 Dark")

        self.root.configure(bg=c["app_bg"])
        self.header_frame.configure(bg=c["app_bg"])
        for parent in self.header_frame.winfo_children():
            parent.configure(bg=c["app_bg"])
            for child in parent.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=c["app_bg"])

        self.title_label.configure(fg=c["text_primary"])
        self.sub_header.configure(fg=c["text_secondary"])
        self.theme_btn.configure(
            bg=c["chip_bg"], fg=c["text_primary"], activebackground=c["chip_hover"]
        )
        self.help_btn.configure(
            bg=c["chip_bg"], fg=c["accent"], activebackground=c["chip_hover"]
        )
        self.main_frame.configure(bg=c["app_bg"])

        for card in self.cards:
            card.configure(
                bg=c["card_bg"],
                highlightbackground=c["card_border"] if card.cget("highlightthickness") else None,
            )

        self.kpi_card.configure(bg=c["kpi_bg"], highlightbackground=c["kpi_border"])
        self.kpi_move_val.configure(bg=c["kpi_bg"], fg=c["accent"])
        self.kpi_office_val.configure(bg=c["kpi_bg"], fg=c["text_primary"])
        self.kpi_meals_val.configure(bg=c["kpi_bg"], fg=c["text_secondary"])

        for lbl in self.sub_labels:
            lbl.configure(bg=c["card_bg"], fg=c["text_secondary"])

        for chip in self.chips:
            chip.configure(
                bg=c["chip_bg"],
                fg=c["chip_accent_fg"],
                activebackground=c["chip_hover"],
            )

        for btn, style in self.buttons:
            parent_bg = btn.master.cget("bg")
            if style == "prim":
                btn.update_style(c["accent"], c["accent_hover"], "#FFFFFF", parent_bg)
            else:
                btn.update_style(c["btn_sec_bg"], c["btn_sec_hover"], c["btn_sec_fg"], parent_bg)

        self.text_container.configure(bg=c["input_border"])
        self.food_text.configure(
            bg=c["input_bg"], fg=c["text_primary"], insertbackground=c["text_primary"]
        )
        self.queue_label.configure(bg=c["card_bg"], fg=c["text_secondary"])
        self.status_label.configure(bg=c["card_bg"])

    def _add_date_navigator(self, parent):
        row = tk.Frame(parent, bg=self.colors["card_bg"])
        row.pack(fill="x", pady=4)
        self.cards.append(row)

        lbl = tk.Label(
            row,
            text="📅 Date (YYYY-MM-DD)",
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        lbl.pack(side="left")
        self.sub_labels.append(lbl)

        right_box = tk.Frame(row, bg=self.colors["card_bg"])
        right_box.pack(side="right")
        self.cards.append(right_box)

        # Prev Day button (<)
        tk.Button(
            right_box,
            text="◀",
            command=lambda: self._shift_date(-1),
            bg=self.colors["chip_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(0, 4))

        border = tk.Frame(right_box, bg=self.colors["input_border"], padx=1, pady=1)
        border.pack(side="left")

        entry = tk.Entry(
            border,
            width=13,
            font=("Segoe UI", 10),
            bg=self.colors["input_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=4,
            justify="center",
        )
        entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        entry.pack()
        self.entries["date"] = entry

        # Today button
        tk.Button(
            right_box,
            text="Today",
            command=self._set_today,
            bg=self.colors["chip_bg"],
            fg=self.colors["accent"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(4, 4))

        # Next Day button (>)
        tk.Button(
            right_box,
            text="▶",
            command=lambda: self._shift_date(1),
            bg=self.colors["chip_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side="left")

    def _shift_date(self, days: int):
        raw = self.entries["date"].get().strip()
        try:
            cur = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            cur = datetime.now()
        new_d = cur + timedelta(days=days)
        self.entries["date"].delete(0, tk.END)
        self.entries["date"].insert(0, new_d.strftime("%Y-%m-%d"))
        self._show_toast(f"Date set to {new_d.strftime('%A, %b %d')}")

    def _add_wake_up_row(self, parent):
        row = tk.Frame(parent, bg=self.colors["card_bg"])
        row.pack(fill="x", pady=4)
        self.cards.append(row)

        lbl = tk.Label(
            row,
            text="☀️ Wake Up Time",
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        lbl.pack(side="left")
        self.sub_labels.append(lbl)

        right_box = tk.Frame(row, bg=self.colors["card_bg"])
        right_box.pack(side="right")
        self.cards.append(right_box)

        # Quick preset pills
        presets = ["6:00 AM", "6:30 AM", "7:00 AM", "7:30 AM"]
        for p in presets:
            tk.Button(
                right_box,
                text=p,
                command=lambda val=p: self._set_wake_up(val),
                bg=self.colors["chip_bg"],
                fg=self.colors["text_secondary"],
                relief="flat",
                bd=0,
                padx=5,
                pady=2,
                font=("Segoe UI", 8),
                cursor="hand2",
            ).pack(side="left", padx=(0, 3))

        border = tk.Frame(right_box, bg=self.colors["input_border"], padx=1, pady=1)
        border.pack(side="left", padx=(2, 0))

        entry = tk.Entry(
            border,
            width=10,
            font=("Segoe UI", 10),
            bg=self.colors["input_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=4,
            justify="center",
        )
        entry.pack()
        self.entries["wake_up"] = entry

        tk.Button(
            right_box,
            text="Now",
            command=self._set_current_time,
            bg=self.colors["chip_bg"],
            fg=self.colors["accent"],
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).pack(side="left", padx=(4, 0))

    def _set_wake_up(self, time_str):
        self.entries["wake_up"].delete(0, tk.END)
        self.entries["wake_up"].insert(0, time_str)
        self._show_toast(f"Wake Up set to {time_str}")

    def _add_stepper_row(
        self,
        parent,
        icon,
        label,
        key,
        default="0",
        step=5,
        presets=None,
        is_float=False,
    ):
        row = tk.Frame(parent, bg=self.colors["card_bg"])
        row.pack(fill="x", pady=4)
        self.cards.append(row)

        lbl = tk.Label(
            row,
            text=f"{icon} {label}",
            bg=self.colors["card_bg"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        lbl.pack(side="left")
        self.sub_labels.append(lbl)

        right_box = tk.Frame(row, bg=self.colors["card_bg"])
        right_box.pack(side="right")
        self.cards.append(right_box)

        # Quick preset buttons
        if presets:
            for p_label, p_delta in presets:
                tk.Button(
                    right_box,
                    text=p_label,
                    command=lambda k=key, d=p_delta, fl=is_float: self._adjust_numeric(
                        k, d, fl
                    ),
                    bg=self.colors["chip_bg"],
                    fg=self.colors["text_secondary"],
                    relief="flat",
                    bd=0,
                    padx=6,
                    pady=2,
                    font=("Segoe UI", 8),
                    cursor="hand2",
                ).pack(side="left", padx=(0, 4))

        # Inline Stepper [-] Entry [+]
        tk.Button(
            right_box,
            text="−",
            command=lambda k=key, s=-step, fl=is_float: self._adjust_numeric(
                k, s, fl
            ),
            bg=self.colors["btn_sec_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=0,
            padx=7,
            pady=1,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left")

        border = tk.Frame(right_box, bg=self.colors["input_border"], padx=1, pady=1)
        border.pack(side="left", padx=2)

        entry = tk.Entry(
            border,
            width=7,
            justify="center",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["input_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=4,
        )
        entry.insert(0, default)
        entry.pack()
        self.entries[key] = entry
        entry.bind("<KeyRelease>", lambda _e: self.update_kpi_summary())

        tk.Button(
            right_box,
            text="+",
            command=lambda k=key, s=step, fl=is_float: self._adjust_numeric(
                k, s, fl
            ),
            bg=self.colors["btn_sec_bg"],
            fg=self.colors["text_primary"],
            relief="flat",
            bd=0,
            padx=7,
            pady=1,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(side="left")

    def _adjust_numeric(self, key, delta, is_float=False):
        entry = self.entries[key]
        raw = entry.get().strip()
        try:
            current = float(raw) if raw else 0.0
        except ValueError:
            current = 0.0

        if delta == 0:
            new_val = 0.0
        else:
            new_val = current + delta
            if new_val < 0:
                new_val = 0.0

        entry.delete(0, tk.END)
        if is_float:
            formatted = f"{new_val:g}"
            entry.insert(0, formatted)
        else:
            entry.insert(0, str(int(round(new_val))))

        self.update_kpi_summary()

    def update_kpi_summary(self):
        try:
            r = float(self.entries["run_time"].get().strip() or "0")
        except (ValueError, KeyError):
            r = 0.0
        try:
            w = float(self.entries["walk_time"].get().strip() or "0")
        except (ValueError, KeyError):
            w = 0.0
        try:
            o = float(self.entries["office_time"].get().strip() or "0")
        except (ValueError, KeyError):
            o = 0.0
        try:
            m = int(round(float(self.entries["meal_count"].get().strip() or "0")))
        except (ValueError, KeyError):
            m = 0

        total_move = int(round(r + w))
        self.kpi_move_val.config(text=f"🏃 {total_move}m Active")
        self.kpi_office_val.config(text=f"💼 {o:g}h Office")
        self.kpi_meals_val.config(text=f"🍽️ {m} Meal{'s' if m != 1 else ''}")

    def _set_today(self):
        self.entries["date"].delete(0, tk.END)
        self.entries["date"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self._show_toast("Date reset to Today")

    def _set_current_time(self):
        now_str = datetime.now().strftime("%I:%M %p")
        self.entries["wake_up"].delete(0, tk.END)
        self.entries["wake_up"].insert(0, now_str)
        self._show_toast(f"Wake Up set to {now_str}")

    def _append_meal_chip(self, meal_name):
        existing = self.food_text.get("1.0", tk.END).strip()
        if not existing:
            self.food_text.insert("1.0", meal_name)
        else:
            separator = ", " if not existing.endswith((",", ";")) else " "
            self.food_text.insert(tk.END, f"{separator}{meal_name}")

        # Automatically bump meal count if 0
        cur_count = self.entries["meal_count"].get().strip()
        if cur_count == "0" or not cur_count:
            self.entries["meal_count"].delete(0, tk.END)
            self.entries["meal_count"].insert(0, "1")
            self.update_kpi_summary()

        self._show_toast(f"Added + {meal_name}")

    def _bind_shortcuts(self):
        self.root.bind("<Control-s>", lambda _e: self.save_locally())
        self.root.bind("<Control-Return>", lambda _e: self.sync_to_google())

    def load_queue(self):
        if os.path.exists(LOCAL_QUEUE_FILE):
            with open(LOCAL_QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_queue(self, queue):
        with open(LOCAL_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2)

    def update_queue_status(self):
        count = len(self.load_queue())
        if count == 0:
            self.queue_label.config(
                text="🟢 Local Queue: All synced", fg=self.colors["text_secondary"]
            )
        else:
            self.queue_label.config(
                text=f"🟠 {count} unsynced log{'s' if count != 1 else ''} queued offline",
                fg=self.colors["status_warn"],
            )

    def collect_current_form(self):
        date_val = self.entries["date"].get().strip()
        wake_up = self.entries["wake_up"].get().strip()
        food_details = self.food_text.get("1.0", tk.END).strip().replace("\n", "; ")

        if not date_val or not wake_up:
            return None

        return {
            "date": date_val,
            "wake_up": wake_up,
            "run_time": self.entries["run_time"].get().strip() or "0",
            "walk_time": self.entries["walk_time"].get().strip() or "0",
            "office_time": self.entries["office_time"].get().strip() or "0",
            "meal_count": self.entries["meal_count"].get().strip() or "0",
            "food_details": food_details or "None logged",
        }

    def clear_form(self):
        self._set_today()
        for key in ["wake_up", "run_time", "walk_time", "office_time", "meal_count"]:
            self.entries[key].delete(0, tk.END)
            if key != "wake_up":
                self.entries[key].insert(0, "0")
        self.food_text.delete("1.0", tk.END)
        self.update_kpi_summary()

    def save_locally(self):
        if self.is_syncing:
            return
        entry = self.collect_current_form()
        if not entry:
            self._show_toast("⚠️ Enter at least Date and Wake Up Time", is_error=True)
            return

        queue = self.load_queue()
        queue.append(entry)
        self.save_queue(queue)
        self.clear_form()
        self.update_queue_status()
        self.status_label.config(text="Saved to queue", fg=self.colors["accent"])
        self._show_toast("✓ Entry saved offline to local queue!")

    def sync_to_google(self):
        if self.is_syncing:
            return

        queue = self.load_queue()
        current_entry = self.collect_current_form()

        items_to_sync = list(queue)
        if current_entry:
            items_to_sync.append(current_entry)

        if not items_to_sync:
            self._show_toast("⚠️ Nothing to sync! Fill form or save locally", is_error=True)
            return

        self.is_syncing = True
        self.sync_btn.set_enabled(False)
        self.save_btn.set_enabled(False)
        self.status_label.config(text="Syncing...", fg=self.colors["status_warn"])
        self._show_toast("Syncing with Google Sheets...")

        worker = threading.Thread(
            target=self._sync_worker,
            args=(items_to_sync, current_entry is not None),
            daemon=True,
        )
        worker.start()

    def _sync_worker(self, items_to_sync, included_current_form):
        try:
            worksheet = get_google_sheet()
            sync_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            rows_to_append = [
                [
                    item["date"],
                    item["wake_up"],
                    item["run_time"],
                    item["walk_time"],
                    item["office_time"],
                    item["meal_count"],
                    item["food_details"],
                    sync_timestamp,
                ]
                for item in items_to_sync
            ]

            worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
            self.root.after(
                0, self._on_sync_success, len(rows_to_append), included_current_form
            )

        except Exception as exc:
            self.root.after(0, self._on_sync_error, str(exc))

    def _on_sync_success(self, count, included_current_form):
        self.save_queue([])
        if included_current_form:
            self.clear_form()
        self.update_queue_status()
        self.is_syncing = False
        self.sync_btn.set_enabled(True)
        self.save_btn.set_enabled(True)
        self.status_label.config(text="Synced", fg=self.colors["status_ok"])
        self._show_toast(f"✓ Synced {count} entry/entries to Google Sheets!")

    def _on_sync_error(self, error_message):
        self.update_queue_status()
        self.is_syncing = False
        self.sync_btn.set_enabled(True)
        self.save_btn.set_enabled(True)
        self.status_label.config(text="Sync failed", fg=self.colors["status_err"])
        self._show_toast("✕ Sync failed — see error dialog", is_error=True)
        messagebox.showerror(
            "Sync Failed", f"Could not sync to Google Sheets:\n\n{error_message}"
        )

    def open_help_guide(self):
        c = self.colors
        help_win = tk.Toplevel(self.root)
        help_win.title("Help & Guide - Daily Routine & Food Log")
        help_win.geometry("520x490")
        help_win.configure(bg=c["card_bg"])
        help_win.transient(self.root)

        tk.Label(
            help_win,
            text="📘 How to Use Daily Tracker",
            bg=c["card_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 6))

        guide_text = (
            "1. Routine & Time Navigation\n"
            "   • Click ◀ or ▶ to quickly log past or future days.\n"
            "   • Click preset buttons (e.g. '6:30 AM') or 'Now' for Wake Up Time.\n"
            "   • Use '+' and '−' steppers or quick duration chips for run/walk/office.\n\n"
            "2. Food & Meals\n"
            "   • Click quick meal chips (+ 🥣 Granola, + 🍛 Rice) to append items.\n"
            "   • Type custom meal or snack details in the word-wrapped text area.\n\n"
            "3. Offline Queue & Cloud Sync\n"
            "   • 'Save Locally' (Ctrl+S) stores logs offline in pending_logs.json.\n"
            "   • 'Sync to Google Sheets' (Ctrl+Enter) pushes both pending logs\n"
            "     and your active form directly to your spreadsheet.\n\n"
            "4. Troubleshooting Google Sheets\n"
            "   • Error 403: Add your Gmail account as a Test User in Google Cloud.\n"
            "   • Missing credentials: Place credentials.json next to daily_tracker.py."
        )

        txt = tk.Text(
            help_win,
            bg=c["input_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 9),
            relief="flat",
            bd=8,
            wrap="word",
        )
        txt.insert("1.0", guide_text)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        tk.Button(
            help_win,
            text="Close",
            command=help_win.destroy,
            bg=c["accent"],
            fg="#FFFFFF",
            relief="flat",
            padx=20,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        ).pack(pady=(0, 16))


if __name__ == "__main__":
    root = tk.Tk()
    app = DailyTrackerApp(root)
    root.mainloop()
