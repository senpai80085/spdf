# SPDF - Secure PDF Distribution System v1.0

<div align="center">

[![CI/CD](https://github.com/senpai80085/spdf/actions/workflows/ci.yml/badge.svg)](https://github.com/senpai80085/spdf/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/Rust-stable-orange.svg)](https://www.rust-lang.org/)

**Enterprise-grade secure document distribution with AES-256-GCM encryption, Ed25519 signatures, and license-based access control.**

</div>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SPDF System                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │   Admin User    │     │   End User      │                   │
│  │  (Dashboard)    │     │  (Viewer)       │                   │
│  └────────┬────────┘     └────────┬────────┘                   │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌─────────────────────────────────────────┐                   │
│  │           SPDF Server (FastAPI)          │                   │
│  │  ┌─────────────────────────────────┐    │                   │
│  │  │ API Routes:                      │    │                   │
│  │  │  • /api/license (validation)    │    │                   │
│  │  │  • /api/device (fingerprinting) │    │                   │
│  │  │  • /api/files (conversion)      │    │                   │
│  │  └─────────────────────────────────┘    │                   │
│  │  ┌─────────────────────────────────┐    │                   │
│  │  │ Crypto Module:                   │    │                   │
│  │  │  • AES-256-GCM encryption       │    │                   │
│  │  │  • Ed25519 signing              │    │                   │
│  │  │  • AES-KW key wrapping          │    │                   │
│  │  └─────────────────────────────────┘    │                   │
│  └─────────────────────────────────────────┘                   │
│           │                       │                             │
│           ▼                       ▼                             │
│  ┌────────────────┐     ┌─────────────────────┐                │
│  │  .spdf File    │────▶│  SPDF Viewer        │                │
│  │  (Encrypted)   │     │  (Tauri/Rust)       │                │
│  └────────────────┘     └─────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔐 Security Features

| Feature | Implementation |
|---------|----------------|
| **Encryption** | AES-256-GCM (NIST SP 800-38D) |
| **Signatures** | Ed25519 (RFC 8032) |
| **Key Wrapping** | AES-KW (RFC 3394) |
| **Device Binding** | HMAC-SHA256 hardware fingerprint |
| **Rate Limiting** | 20 requests/minute per IP |
| **Brute Force Protection** | 5 failed attempts = 15min lockout |

## 🚀 Quick Start

### 1. Start the Server

```bash
cd spdf-server
pip install -r requirements.txt
python main.py
```

Server runs at: **http://localhost:8000**

### 2. Admin Dashboard

1. Open http://localhost:8000/admin.html
2. Login: `admin@spdf.local` / `admin123`
3. Upload PDF → Convert to SPDF
4. Create license → Share key with user

### 3. Build the Viewer

```bash
cd spdf-viewer-desktop
npm install
npm run tauri build
```

## 🛠️ CLI Tool

```bash
# Encrypt PDF to SPDF
spdf encrypt input.pdf -o output.spdf --doc-id DOC-001

# Decrypt SPDF to PDF
spdf decrypt input.spdf -o output.pdf --license SPDF-XXXX-XXXX-XXXX-XXXX

# Verify SPDF signature
spdf verify file.spdf

# Create license
spdf license add user@example.com --doc DOC-001 --expires 30
```

## 📁 Project Structure

```
spdf/
├── spdf-server/           # FastAPI backend
│   ├── crypto/            # Encryption, signing, keys
│   │   ├── keys.py        # Key management & wrapping
│   │   ├── encrypt.py     # SPDF creation
│   │   ├── decrypt.py     # SPDF parsing & decryption
│   │   └── signature.py   # Ed25519 operations
│   ├── api/               # REST API endpoints
│   │   ├── license.py     # License validation
│   │   ├── device.py      # Device fingerprinting
│   │   └── files.py       # File operations
│   ├── tests/             # Pytest test suite
│   └── static/            # Admin dashboard
├── spdf-viewer-desktop/   # Tauri desktop viewer
│   ├── src/               # Frontend (TypeScript)
│   └── src-tauri/src/     # Backend (Rust)
│       ├── spdf_parser.rs # File parsing
│       ├── decrypt.rs     # AES-GCM decryption
│       ├── verify.rs      # Signature verification
│       └── device_id.rs   # Device fingerprinting
├── spdf-cli/              # Command-line tool
├── spdf-format/           # Format specification
│   └── spec.md            # SPDF v1.0 specification
└── .github/workflows/     # CI/CD pipeline
```

## 📋 SPDF File Format

```
+-------------------+
|     MAGIC (4B)    |  "SPDF"
+-------------------+
|   VERSION (1B)    |  0x01
+-------------------+
|   FLAGS (2B)      |  Feature flags
+-------------------+
| HEADER_LEN (4B)   |  Big-endian
+-------------------+
|   HEADER (JSON)   |  Metadata
+-------------------+
| WRAPPED_KEY (40B) |  AES-KW wrapped k_doc
+-------------------+
|  NONCE (12B)      |  AES-GCM nonce
+-------------------+
|  CIPHERTEXT       |  Encrypted PDF
+-------------------+
|  AUTH_TAG (16B)   |  GCM tag
+-------------------+
|  SIGNATURE (64B)  |  Ed25519
+-------------------+
```

See [spec.md](spdf-format/spec.md) for full specification.

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SPDF_MASTER_KEY` | 64-char hex master key | Yes (production) |

Generate master key:
```python
import secrets
print(secrets.token_hex(32))
```

## 🧪 Testing

```bash
# Run Python tests
cd spdf-server
pytest tests/ -v --cov

# Run Rust tests
cd spdf-viewer-desktop/src-tauri
cargo test
```

## 🚀 Building for Production

### Windows
```powershell
cd spdf-viewer-desktop
npm run tauri build
# Output: src-tauri/target/release/bundle/msi/*.msi
```

### macOS
```bash
cd spdf-viewer-desktop
npm run tauri build
# Output: src-tauri/target/release/bundle/dmg/*.dmg
```

### Linux
```bash
sudo apt install libwebkit2gtk-4.0-dev build-essential
cd spdf-viewer-desktop
npm run tauri build
# Output: src-tauri/target/release/bundle/appimage/*.AppImage
```

## ⚠️ Security Considerations

### Threat Model
- **Protected**: File tampering, key extraction, device cloning, brute force
- **Not Protected**: Memory attacks, screenshot capture, physical access

### Known Limitations
- Client application integrity is not cryptographically enforced
- Decrypted content exists in memory during viewing
- Cannot prevent screen capture or physical photography

### Best Practices
1. **Rotate master key** periodically using key rotation API
2. **Set expiration dates** on all licenses
3. **Monitor failed attempts** via server logs
4. **Use HTTPS** in production
5. **Store master key** in secure secrets manager

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## 📚 Documentation

- [SPDF Format Specification](spdf-format/spec.md)
- [Build Instructions](BUILD_INSTRUCTIONS.md)
- [Security Documentation](SECURITY.md)
- [Architecture Details](ARCHITECTURE.md)
