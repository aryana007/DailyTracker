import os
import sys
import json
import csv
import io
import socket
import threading
import subprocess
import webbrowser
import http.server
from datetime import datetime
import mimetypes
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Paths & Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
LOCAL_QUEUE_FILE = os.path.join(BASE_DIR, "pending_logs.json")
CACHE_FILE = os.path.join(BASE_DIR, "history_cache.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "user_settings.json")
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

DEFAULT_SETTINGS = {
    "quick_chips": [
        "🥣 Granola & Milk",
        "🍛 Rice & Dal",
        "🫓 Roti & Sabzi",
        "☕ Tea / Coffee",
        "🍎 Fruit / Snack",
        "🥗 Salad / Greens",
    ],
    "water_target": 8,
    "sleep_target": 8.0,
    "theme": "dark",
}

# Live Google Sheet URL
SHEET_URL_CACHE = "https://docs.google.com/spreadsheets/d/1am-hpcSappW5eHXsbzYbPp7xPzhn-PXKfHRwQ5_Tb4k"


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            return dict(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)


def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


def load_queue():
    if os.path.exists(LOCAL_QUEUE_FILE):
        try:
            with open(LOCAL_QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_queue(queue):
    with open(LOCAL_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)


def load_history():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def get_google_sheet():
    """Authenticates user via OAuth and opens/creates the target Google Sheet."""
    global SHEET_URL_CACHE
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

    SHEET_URL_CACHE = spreadsheet.url
    return worksheet


def sync_sheet_to_cache_background():
    """Background worker to sync Google Sheet rows into local history cache."""
    try:
        ws = get_google_sheet()
        rows = ws.get_all_values()
        if len(rows) > 1:
            cache = load_history()
            for r in rows[1:]:
                if r and r[0]:
                    d_key = r[0].strip()
                    cache[d_key] = {
                        "date": d_key,
                        "wake_up": r[1] if len(r) > 1 else "",
                        "run_time": r[2] if len(r) > 2 else "0",
                        "walk_time": r[3] if len(r) > 3 else "0",
                        "office_time": r[4] if len(r) > 4 else "0",
                        "meal_count": r[5] if len(r) > 5 else "0",
                        "food_details": r[6] if len(r) > 6 else "",
                        "synced": True,
                        "synced_at": r[7] if len(r) > 7 else "",
                    }
            save_history(cache)
    except Exception:
        pass


class AppRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Quiet logging

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url_parts = self.path.split("?")
        path = url_parts[0]
        query = url_parts[1] if len(url_parts) > 1 else ""

        if path == "/api/status":
            queue = load_queue()
            cache = load_history()
            self._send_json(
                {
                    "status": "ready",
                    "queue_count": len(queue),
                    "sheet_name": SHEET_NAME,
                    "sheet_url": SHEET_URL_CACHE,
                    "total_history": len(cache),
                }
            )
            return

        elif path == "/api/history":
            cache = load_history()
            queue = load_queue()
            # Merge pending queue entries into history view
            merged = dict(cache)
            for q in queue:
                if q.get("date"):
                    merged[q["date"]] = {**q, "synced": False}
            history_list = [merged[k] for k in sorted(merged.keys(), reverse=True)]
            self._send_json({"history": history_list})
            return

        elif path == "/api/entry":
            params = dict(qp.split("=") for qp in query.split("&") if "=" in qp)
            req_date = params.get("date", "").strip()
            queue = load_queue()
            # Check pending queue first
            for q in reversed(queue):
                if q.get("date") == req_date:
                    self._send_json({"found": True, "entry": q, "source": "queue"})
                    return
            cache = load_history()
            if req_date in cache:
                self._send_json({"found": True, "entry": cache[req_date], "source": "cache"})
                return
            self._send_json({"found": False, "entry": None})
            return

        elif path == "/api/settings":
            self._send_json({"settings": load_settings()})
            return

        elif path == "/api/export_csv":
            cache = load_history()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(HEADERS)
            for date_key in sorted(cache.keys(), reverse=True):
                item = cache[date_key]
                writer.writerow(
                    [
                        item.get("date", ""),
                        item.get("wake_up", ""),
                        item.get("run_time", "0"),
                        item.get("walk_time", "0"),
                        item.get("office_time", "0"),
                        item.get("meal_count", "0"),
                        item.get("food_details", "None logged"),
                        item.get("synced_at", ""),
                    ]
                )
            csv_bytes = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header(
                "Content-Disposition", 'attachment; filename="daily_routine_food_log.csv"'
            )
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        # Serve static web files
        if path == "/":
            rel_file = "index.html"
        else:
            rel_file = path.lstrip("/")

        file_path = os.path.join(WEB_DIR, rel_file)
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            file_path = os.path.join(WEB_DIR, "index.html")

        if os.path.exists(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "text/plain"
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            data = {}

        path = self.path.split("?")[0]

        if path == "/api/save":
            if not data or not data.get("date") or not data.get("wake_up"):
                self._send_json(
                    {"success": False, "error": "Missing Date or Wake Up Time."}, status=400
                )
                return
            queue = load_queue()
            queue.append(data)
            save_queue(queue)

            # Update local history cache as well
            cache = load_history()
            cache[data["date"]] = {**data, "synced": False, "synced_at": "Offline Queue"}
            save_history(cache)

            self._send_json({"success": True, "queue_count": len(queue)})
            return

        elif path == "/api/sync":
            queue = load_queue()
            current_form = data.get("current")
            items = list(queue)
            if current_form and current_form.get("date") and current_form.get("wake_up"):
                items.append(current_form)

            if not items:
                self._send_json({"success": False, "error": "No items to sync."}, status=400)
                return

            try:
                worksheet = get_google_sheet()
                sync_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows_to_append = [
                    [
                        item.get("date", ""),
                        item.get("wake_up", ""),
                        item.get("run_time", "0"),
                        item.get("walk_time", "0"),
                        item.get("office_time", "0"),
                        item.get("meal_count", "0"),
                        item.get("food_details", "None logged"),
                        sync_timestamp,
                    ]
                    for item in items
                ]
                worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                save_queue([])  # Clear queue on success

                # Update history cache with synced state
                cache = load_history()
                for item in items:
                    if item.get("date"):
                        cache[item["date"]] = {**item, "synced": True, "synced_at": sync_timestamp}
                save_history(cache)

                self._send_json(
                    {
                        "success": True,
                        "count": len(rows_to_append),
                        "sheet_url": SHEET_URL_CACHE,
                    }
                )
            except Exception as exc:
                self._send_json({"success": False, "error": str(exc)}, status=500)
            return

        elif path == "/api/open_sheet":
            sheet_url = SHEET_URL_CACHE
            webbrowser.open(sheet_url)
            self._send_json({"success": True, "url": sheet_url})
            return

        elif path == "/api/settings":
            if data:
                save_settings(data)
                self._send_json({"success": True, "settings": load_settings()})
            else:
                self._send_json({"success": False}, status=400)
            return

        self.send_response(404)
        self.end_headers()


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def launch_desktop_app():
    port = find_free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), AppRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Pre-sync latest sheet rows in background
    threading.Thread(target=sync_sheet_to_cache_background, daemon=True).start()

    app_url = f"http://127.0.0.1:{port}"

    # Try pywebview first
    pywebview_started = False
    try:
        import webview
        w = webview.create_window(
            title="Daily Routine & Food Log",
            url=app_url,
            width=540,
            height=760,
            min_size=(480, 680),
            resizable=True,
            background_color="#090D16",
        )
        webview.start()
        pywebview_started = True
    except Exception:
        pywebview_started = False

    # Fallback to Microsoft Edge native App Mode
    if not pywebview_started:
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)
        if edge_bin:
            edge_cmd = [
                edge_bin,
                f"--app={app_url}",
                "--window-size=540,760",
                "--app-title=Daily Routine & Food Log",
            ]
            proc = subprocess.Popen(edge_cmd)
            proc.wait()
        else:
            webbrowser.open(app_url)

    server.shutdown()


if __name__ == "__main__":
    launch_desktop_app()
