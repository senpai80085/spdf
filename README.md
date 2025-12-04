# 🔒 SPDF v1 - Secure Portable Document Format

A lightweight, self-hosted, open-source system for secure document distribution with encryption, digital signatures, and device-bound access control.

## ✨ Features

- **🔐 AES-256-GCM Encryption** - Military-grade PDF encryption
- **✍️ Ed25519 Signatures** - Tamper-proof digital signatures
- **📱 Device-Bound Access** - Hardware UUID-based device limits
- **📄 License Management** - Control who can access documents
- **💧 Watermarks** - Dynamic user/device watermarks
- **🚫 Permission Enforcement** - Disable print/copy in viewer
- **🏠 Self-Hosted** - Complete control over your data

## 🏗️ Architecture

The system consists of 4 components:

| Component | Description | Tech Stack |
|-----------|-------------|------------|
| **spdf-format** | Binary format library | Python, cryptography |
| **spdf-cli** | PDF → SPDF converter | Python, PyMuPDF |
| **spdf-server** | Backend API | FastAPI, SQLite, SQLAlchemy |
| **spdf-viewer-desktop** | Desktop viewer | Tauri, Rust, TypeScript, pdf.js |

## 📁 Project Structure

```
spdf/
├── spdf-format/              # Core SPDF library
│   ├── spdf_format.py        # Binary format read/write
│   └── requirements.txt
│
├── spdf-cli/                 # PDF to SPDF converter
│   ├── cli.py                # Main CLI tool
│   ├── key_manager.py        # Ed25519 key management
│   ├── debug_decrypt.py      # Testing utility
│   └── requirements.txt
│
├── spdf-server/              # FastAPI backend
│   ├── main.py               # FastAPI app
│   ├── models.py             # Database models
│   ├── config.py             # K_master + settings
│   ├── database.py           # SQLAlchemy setup
│   ├── admin_setup.py        # Test user creation
│   ├── routes/
│   │   ├── auth.py           # JWT authentication
│   │   ├── keys.py           # Key distribution
│   │   └── documents.py      # Document management
│   └── requirements.txt
│
├── spdf-viewer-desktop/      # Tauri desktop app
│   ├── src-tauri/src/
│   │   ├── main.rs           # Tauri backend
│   │   └── spdf.rs           # SPDF file handling
│   ├── src/
│   │   ├── main.ts           # Frontend logic
│   │   └── styles.css        # UI styling
│   ├── index.html
│   └── package.json
│
├── test.pdf                  # Sample PDF for testing
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- Rust (for Tauri viewer)

### Step 1: Install Dependencies

```bash
# CLI + Format Library
cd spdf-cli
pip install PyMuPDF cryptography

# Server
cd ../spdf-server
pip install -r requirements.txt

# Viewer (requires Rust and Node.js)
cd ../spdf-viewer-desktop
npm install
```

### Step 2: Create a Test SPDF

```bash
cd spdf-cli
python cli.py convert \
  --input ../test.pdf \
  --output ../test.spdf \
  --doc-id DOC-1 \
  --org-id ORG-1 \
  --server-url http://localhost:8000
```

This creates:
- `test.spdf` - Encrypted, signed SPDF file
- `test.spdf.key` - Encryption key (for testing only)

### Step 3: Start the Server

```bash
cd ../spdf-server

# Setup test user and license
python admin_setup.py

# Start server
python main.py
```

Server runs on `http://localhost:8000`

**Test Credentials:**
- Email: `test@example.com`
- Password: `test123`

### Step 4: Open Viewer

```bash
cd ../spdf-viewer-desktop
npm run tauri dev
```

Click "📁 Open SPDF" and select your `.spdf` file!

## 📖 Usage Guide

### Converting PDFs to SPDF

```bash
python cli.py convert \
  --input document.pdf \
  --output secure_doc.spdf \
  --doc-id DOC-001 \
  --org-id MY-ORG \
  --server-url https://your-server.com \
  --allow-print \           # Optional: enable printing
  --allow-copy \            # Optional: enable copying
  --max-devices 5           # Max devices (default: 2)
```

### Managing Users (Server)

```python
# In spdf-server directory
from database import SessionLocal
from models import User, License
from routes.auth import get_password_hash

db = SessionLocal()

# Create user
user = User(
    email="user@example.com",
    password_hash=get_password_hash("password123"),
    org_id="ORG-1"
)
db.add(user)

# Grant license
license = License(
    user_id=user.id,
    doc_id="DOC-001",
    max_devices=3
)
db.add(license)
db.commit()
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | Login with email/password → JWT |
| `/auth/register` | POST | Create new user |
| `/keys/get` | POST | Get K_doc for document |
| `/docs/upload` | POST | Upload SPDF file |
| `/docs/{doc_id}/download` | GET | Download SPDF |
| `/docs/list` | GET | List user's documents |

API docs available at: `http://localhost:8000/docs`

## 🔒 Security Features

### Encryption
- **AES-256-GCM** for PDF content
- Random 96-bit nonce per document
- 128-bit authentication tag

### Digital Signatures
- **Ed25519** (Curve25519) signatures
- Signs: MAGIC + VERSION + HEADER + CONTENT
- Detects any file tampering

### Key Management
- **K_master**: 256-bit AES key for server-side K_doc encryption
- **K_doc**: 256-bit per-document encryption key
- **Ed25519 keypairs**: Per-organization signing keys

### Access Control
- **Device binding**: Hardware UUID-based device limits
- **License system**: Control user access per document
- **JWT authentication**: 24-hour token expiry

## 🎨 Viewer Features

- **Modern dark theme** with gradient UI
- **Page navigation** - Previous/Next with counter
- **Zoom controls** - 0.5x to 3.0x scaling
- **Watermark overlay** - Dynamic user/device watermarks
- **Permission enforcement**:
  - Disable text selection (copy protection)
  - Block Ctrl+P (print protection)
- **Status notifications** - Real-time feedback

## 🧪 Testing

### Test CLI Conversion

```bash
cd spdf-cli
python cli.py convert --input ../test.pdf --output test.spdf --doc-id DOC-1 --org-id ORG-1 --server-url http://localhost:8000
```

### Test Decryption

```bash
python debug_decrypt.py test.spdf --key test.spdf.key --org-id ORG-1
```

### Test Server

```bash
cd ../spdf-server
python main.py
# Visit http://localhost:8000/docs for API testing
```

### Test Viewer

```bash
cd ../spdf-viewer-desktop
npm run tauri dev
```

## 📝 File Format Specification

### SPDF Binary Structure

```
Offset  Size  Field          Description
------  ----  -------------  ----------------------------------
0       4     MAGIC          "SPDF" (0x53 0x50 0x44 0x46)
4       1     VERSION        1 (uint8)
5       4     HEADER_LEN     Header JSON length (uint32 BE)
9       N     HEADER_JSON    UTF-8 encoded JSON
9+N     M     CONTENT        nonce(12) + ciphertext + tag(16)
9+N+M   64    SIGNATURE      Ed25519 signature (64 bytes)
```

### Header JSON Schema

```json
{
  "spdf_version": "1.0",
  "doc_id": "DOC-1",
  "org_id": "ORG-1",
  "server_url": "https://example.com",
  "created_at": "2025-12-04T00:00:00Z",
  "permissions": {
    "allow_print": false,
    "allow_copy": false,
    "max_devices": 2
  },
  "watermark": {
    "enabled": true,
    "text": "{{user_id}} | {{device_id}}"
  }
}
```

## 🛠️ Development

### Build Viewer for Production

```bash
cd spdf-viewer-desktop
npm run tauri build
```

Creates installers for Windows/Linux/macOS in `src-tauri/target/release/bundle/`

### Server in Production

```bash
# Use proper WSGI server
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

**Production Checklist:**
- [ ] Change `SECRET_KEY` in config.py
- [ ] Backup `.k_master` file securely
- [ ] Use HTTPS for server
- [ ] Restrict CORS origins
- [ ] Set up database backups

## 📄 License

Open source - use however you like!

## 🤝 Contributing

This is a v1 implementation focused on core functionality. Future enhancements could include:

- Post-quantum cryptography (Kyber, Dilithium)
- Key rotation mechanisms
- Audit logging
- Admin dashboard UI
- Mobile viewers (iOS/Android)
- Cloud storage integration

## 📚 Documentation

- [Walkthrough](file:///C:/Users/PRIYANSHU/.gemini/antigravity/brain/a6a3ef21-a6ec-4011-81e5-d0d3134364c4/walkthrough.md) - Complete implementation walkthrough
- [Implementation Plan](file:///C:/Users/PRIYANSHU/.gemini/antigravity/brain/a6a3ef21-a6ec-4011-81e5-d0d3134364c4/implementation_plan.md) - Technical architecture details
- [Task List](file:///C:/Users/PRIYANSHU/.gemini/antigravity/brain/a6a3ef21-a6ec-4011-81e5-d0d3134364c4/task.md) - Implementation progress

## 🎯 Current Status

✅ **Phase 1**: SPDF Format + CLI - Complete  
✅ **Phase 2**: Desktop Viewer - Complete  
✅ **Phase 3**: Server Backend - Complete  
⏳ **Phase 4**: Viewer-Server Integration - Ready to implement  
⏳ **Phase 5**: Full Permissions + Watermarks - Ready to implement

---

**Built with** ❤️ **using Python, Rust, and TypeScript**
