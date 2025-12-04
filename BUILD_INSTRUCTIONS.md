# SPDF Viewer - Cross-Platform Build Instructions

This guide explains how to build the SPDF Viewer for Windows (EXE), macOS (DMG/APP), Linux (AppImage), and Android (APK).

## Prerequisites

### All Platforms
- **Node.js** (v18 or later)
- **Rust** (latest stable version)
- **Tauri CLI**: `npm install -g @tauri-apps/cli`

### Platform-Specific Requirements

#### Windows (EXE)
- **Visual Studio Build Tools** or **Visual Studio 2019/2022** with C++ development tools
- **WebView2** (usually pre-installed on Windows 10/11)

#### macOS (DMG/APP)
- **Xcode** (latest version from App Store)
- **Xcode Command Line Tools**: `xcode-select --install`

#### Linux (AppImage)
- **Build essentials**: `sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev`
- **AppImage tools**: `sudo apt install appimagetool`

#### Android (APK)
- **Android Studio** with Android SDK
- **Android NDK** (r25c or later)
- **Java JDK** (11 or later)
- **Tauri Mobile**: `cargo install tauri-cli --version "^2.0.0-beta"`

---

## Build Instructions

### 1. Windows (EXE)

```powershell
# Navigate to viewer directory
cd spdf-viewer-desktop

# Install dependencies
npm install

# Build for Windows
npm run tauri build

# Output location:
# src-tauri/target/release/spdf-viewer.exe
# src-tauri/target/release/bundle/msi/SPDF Viewer_X.X.X_x64_en-US.msi
```

**Distribution:**
- Distribute the `.msi` installer for easy installation
- Or distribute the standalone `.exe` (requires WebView2 runtime)

---

### 2. macOS (DMG/APP)

```bash
# Navigate to viewer directory
cd spdf-viewer-desktop

# Install dependencies
npm install

# Build for macOS
npm run tauri build

# Output location:
# src-tauri/target/release/bundle/macos/SPDF Viewer.app
# src-tauri/target/release/bundle/dmg/SPDF Viewer_X.X.X_x64.dmg
```

**Code Signing (for distribution):**
```bash
# Sign the app (requires Apple Developer account)
codesign --deep --force --verify --verbose --sign "Developer ID Application: YOUR_NAME" "SPDF Viewer.app"

# Notarize for Gatekeeper
xcrun notarytool submit "SPDF Viewer.dmg" --apple-id "your@email.com" --password "app-specific-password" --team-id "TEAM_ID"
```

---

### 3. Linux (AppImage)

```bash
# Navigate to viewer directory
cd spdf-viewer-desktop

# Install dependencies
npm install

# Build for Linux
npm run tauri build

# Output location:
# src-tauri/target/release/bundle/appimage/spdf-viewer_X.X.X_amd64.AppImage
# src-tauri/target/release/bundle/deb/spdf-viewer_X.X.X_amd64.deb
```

**Distribution:**
- `.AppImage` - Portable, works on most Linux distributions
- `.deb` - For Debian/Ubuntu-based systems
- `.rpm` - For Red Hat/Fedora-based systems (configure in `tauri.conf.json`)

---

### 4. Android (APK)

> **Note:** Tauri Mobile support is in beta. This requires Tauri v2.0+

#### Initial Setup

```bash
# Install Tauri Mobile CLI
cargo install tauri-cli --version "^2.0.0-beta"

# Add Android target
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android

# Initialize Tauri Mobile
cd spdf-viewer-desktop
cargo tauri android init
```

#### Configure Android

Edit `src-tauri/gen/android/app/build.gradle.kts`:
```kotlin
android {
    namespace = "com.spdf.viewer"
    compileSdk = 34
    
    defaultConfig {
        applicationId = "com.spdf.viewer"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }
}
```

#### Build APK

```bash
# Development build
cargo tauri android dev

# Production build
cargo tauri android build

# Output location:
# src-tauri/gen/android/app/build/outputs/apk/release/app-release.apk
```

#### Sign APK for Release

```bash
# Generate keystore (first time only)
keytool -genkey -v -keystore spdf-viewer.keystore -alias spdf -keyalg RSA -keysize 2048 -validity 10000

# Sign the APK
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore spdf-viewer.keystore app-release-unsigned.apk spdf

# Align the APK
zipalign -v 4 app-release-unsigned.apk spdf-viewer.apk
```

---

## iOS (IPA) - Future Support

> **Note:** iOS support requires Tauri v2.0+ and is currently in beta

```bash
# Add iOS target
rustup target add aarch64-apple-ios x86_64-apple-ios

# Initialize iOS
cargo tauri ios init

# Build for iOS
cargo tauri ios build

# Requires:
# - macOS with Xcode
# - Apple Developer account ($99/year)
# - Provisioning profiles and certificates
```

---

## Configuration

### Customize Build Settings

Edit `src-tauri/tauri.conf.json`:

```json
{
  "productName": "SPDF Viewer",
  "version": "1.0.0",
  "identifier": "com.spdf.viewer",
  "build": {
    "beforeBuildCommand": "npm run build",
    "beforeDevCommand": "npm run dev",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../dist"
  },
  "bundle": {
    "active": true,
    "targets": ["msi", "dmg", "appimage", "deb"],
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

---

## Troubleshooting

### Windows
- **Error: WebView2 not found** → Install WebView2 Runtime from Microsoft
- **Build fails** → Ensure Visual Studio Build Tools are installed

### macOS
- **Code signing fails** → Check Apple Developer account and certificates
- **App won't open** → Right-click → Open (for unsigned apps)

### Linux
- **Missing dependencies** → Install webkit2gtk and other required libraries
- **AppImage won't run** → Make executable: `chmod +x *.AppImage`

### Android
- **SDK not found** → Set `ANDROID_HOME` environment variable
- **NDK errors** → Ensure NDK r25c+ is installed via Android Studio

---

## Distribution Checklist

- [ ] Test on target platform
- [ ] Sign binaries (Windows/macOS/Android)
- [ ] Create installer/package
- [ ] Test installation process
- [ ] Prepare release notes
- [ ] Upload to distribution platform (GitHub Releases, App Store, Play Store, etc.)

---

## Automated CI/CD

### GitHub Actions Example

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: windows-installer
          path: src-tauri/target/release/bundle/msi/*.msi

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: macos-dmg
          path: src-tauri/target/release/bundle/dmg/*.dmg

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: sudo apt update && sudo apt install -y libwebkit2gtk-4.0-dev build-essential curl wget libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: linux-appimage
          path: src-tauri/target/release/bundle/appimage/*.AppImage
```

---

## Additional Resources

- [Tauri Documentation](https://tauri.app)
- [Tauri Mobile Guide](https://beta.tauri.app/guides/build/mobile/)
- [Code Signing Guide](https://tauri.app/v1/guides/distribution/sign-windows)
- [Publishing to Stores](https://tauri.app/v1/guides/distribution/publishing)
