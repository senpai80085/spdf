# SPDF - Secure PDF Distribution System

A secure document distribution system with encrypted PDFs, license-based access, and a Galaxy-themed admin dashboard.

## 🚀 Quick Start (2 minutes)

### 1. Start the Server
```bash
cd spdf-server
pip install -r requirements.txt
python main.py
```
Server runs at: **http://localhost:8000**

### 2. Login to Admin Dashboard
- Open http://localhost:8000/admin.html
- Login: `admin@spdf.local` / `admin123`

### 3. Upload a PDF
1. Go to **Upload PDF** tab
2. Click upload zone → select PDF
3. Enter Doc ID (e.g., `DOC-001`) and Title
4. Click **Convert to SPDF**

### 4. Create a License
1. **Users** tab → **Add User** (create end-user)
2. **Licenses** tab → **Add License**
3. Copy the license key (auto-copied)

---

## 🖥️ Build SPDF Viewer

### Prerequisites (All Platforms)
- Node.js 18+
- Rust (https://rustup.rs)

### Windows
```powershell
# Install build tools
winget install Microsoft.VisualStudio.2022.BuildTools

cd spdf-viewer-desktop
npm install
npm run tauri build
```
Output: `src-tauri/target/release/spdf-viewer.exe`

### macOS
```bash
# Install Xcode CLI
xcode-select --install

cd spdf-viewer-desktop
npm install
npm run tauri build
```
Output: `src-tauri/target/release/bundle/dmg/SPDF Viewer.dmg`

### Linux (Ubuntu/Debian)
```bash
# Install dependencies
sudo apt update
sudo apt install libwebkit2gtk-4.0-dev build-essential curl wget libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

cd spdf-viewer-desktop
npm install
npm run tauri build
```
Output: `src-tauri/target/release/bundle/deb/spdf-viewer.deb`

---

## 🔐 Features

- **AES-256-GCM** encryption for documents
- **Ed25519** digital signatures
- **License key** authentication
- **Device limiting** per license
- **Galaxy-themed** admin dashboard
- **Cross-platform** desktop viewer (Windows/Mac/Linux)

## 📁 Project Structure

```
spdf/
├── spdf-server/         # FastAPI backend
│   ├── main.py          # Server entry point
│   ├── routes/          # API endpoints
│   └── static/          # Admin dashboard
├── spdf-viewer-desktop/ # Tauri desktop viewer
│   ├── src/             # Frontend
│   └── src-tauri/       # Rust backend
└── BUILD_INSTRUCTIONS.md
```

## License

MIT
