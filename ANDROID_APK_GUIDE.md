# 📱 Android APK Build Guide (Capacitor)

Your `web/` folder is pre-configured and 100% ready to be packaged directly into a native Android APK using **Capacitor**.

---

### Prerequisites
1. **Node.js** (npm) installed on your PC.
2. **Android Studio** (with Android SDK) installed on your PC.

---

### Step-by-Step Commands to Generate APK

Open a terminal or PowerShell in `C:\Users\dell\Desktop\DailyTracker\web`:

```bash
cd C:\Users\dell\Desktop\DailyTracker\web

# 1. Install Capacitor dependencies
npm install

# 2. Add the native Android project
npx cap add android

# 3. Sync the web files to Android
npx cap sync android

# 4. Open in Android Studio to build or run on your phone
npx cap open android
```

In **Android Studio**:
* Click **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
* Your completed `.apk` file will be generated in `android/app/build/outputs/apk/debug/app-debug.apk`!
* Transfer it to your phone or install via USB debugging.
