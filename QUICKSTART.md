# SPDF Quick Start Guide

## 🚀 Start the Server (2 minutes)

```bash
cd spdf-server
pip install -r requirements.txt
python main.py
```

Server runs at: **http://localhost:8000**

---

## 👤 First-Time Setup

1. Open http://localhost:8000/admin.html
2. Login: `admin@spdf.local` / `admin123`

---

## 📄 Upload a PDF

1. Go to **Upload PDF** tab
2. Click upload zone → select PDF
3. Enter Doc ID (e.g., `DOC-001`) and Title
4. Click **Convert to SPDF**

---

## 🔑 Create a License

1. Go to **Users** tab → **Add User** (create end-user account)
2. Go to **Licenses** tab → **Add License**
   - Enter User ID and Doc ID
   - Click **Create License**
3. **Copy the license key** (auto-copied to clipboard)

---

## 📱 View SPDF (End User)

1. Build viewer: `cd spdf-viewer-desktop && npm install && npm run tauri build`
2. Open `.spdf` file in viewer
3. Enter license key when prompted
4. Document unlocks!

---

## 🔐 That's It!

- **Admin**: Upload PDFs, manage users, create licenses
- **Users**: Get license key, view secured documents

For detailed build instructions, see `BUILD_INSTRUCTIONS.md`
