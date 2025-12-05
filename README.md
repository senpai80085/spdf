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
   - Enter User ID and Doc ID
   - Click **Create License**
3. Copy the license key (auto-copied)

### 5. View SPDF (End User)
```bash
cd spdf-viewer-desktop
npm install
npm run tauri build
```
Open `.spdf` file → Enter license key → Done!

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
├── BUILD_INSTRUCTIONS.md
└── QUICKSTART.md
```

## 📖 Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Build Instructions](BUILD_INSTRUCTIONS.md)

## License

MIT
