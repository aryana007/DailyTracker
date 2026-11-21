# ⏱️ Daily Routine & Food Tracker

A modern, glassmorphic daily activity, habit, and nutrition tracker with real-time bidirectional Google Sheets synchronization and native Android APK capability.

---

## 🌟 Key Features

- **Modern Glassmorphic UI**: Linear / Raycast dark-mode aesthetic with custom pure CSS, KPI quick-stat cards, habit chips, and fluid interactions.
- **Bi-directional Google Sheets Sync**:
  - Live 2-way sync with your Google Sheet.
  - Automatic retry queue (`pending_logs.json`) for seamless offline operation.
  - Smart row deduplication (merges edits into existing date entries).
- **Desktop & Native Experience**:
  - Native Windows desktop application powered by `pywebview` with zero-latency local REST API.
  - One-click launcher shortcuts with custom `.ico` branding.
  - Classic Tkinter GUI preserved in `daily_tracker_classic.py`.
- **Analytics & History**:
  - 7-day movement trend chart (Active minutes, Steps, Deep Work).
  - Searchable, filterable history log with 1-click entry editing.
  - CSV report export.
- **📱 Android APK Ready**:
  - Self-contained web client ready for Capacitor/Android Studio packaging.
  - Responsive layout optimized for mobile screens.

---

## 📂 Project Architecture

```
DailyTracker/
├── web/
│   ├── index.html              # Modern responsive Webview UI
│   ├── style.css               # Pure CSS glassmorphism & responsive layouts
│   ├── app.js                  # Frontend state management & REST client
│   ├── capacitor.config.json   # Android Capacitor configuration
│   └── package.json            # Capacitor dependencies
├── daily_tracker.py            # Primary app: Local HTTP API + pywebview launcher
├── daily_tracker_classic.py    # Classic Tkinter edition
├── code_patcher.py             # Safe code patching utility with AST validation
├── logo.ico / logo.png         # App branding assets
├── Launch_Daily_Tracker.bat    # Windows batch launcher
├── Launch_Daily_Tracker.vbs    # Background runner (no console window)
├── ANDROID_APK_GUIDE.md        # Step-by-step instructions for Android APK
└── README.md
```

---

## 🚀 Quick Start (Windows)

### Requirements
- Python 3.10+
- Installed packages:
  ```bash
  pip install pywebview gspread google-auth pillow
  ```

### Running the App
- Double-click **`Daily Tracker.lnk`** on your desktop, OR
- Run:
  ```bash
  python daily_tracker.py
  ```

---

## 🔒 Security Note
Authentication credentials (`credentials.json` and `token.json`) and personal tracking history are excluded from version control via `.gitignore`. Place your Google Cloud service account or OAuth credentials in the root directory before initiating Google Sheets sync.

---

## 📱 Building the Android APK
Refer to [`ANDROID_APK_GUIDE.md`](ANDROID_APK_GUIDE.md) for step-by-step instructions to compile the frontend into a standalone Android APK using Capacitor and Android Studio.
