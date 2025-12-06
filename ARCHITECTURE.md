# SPDF Architecture Documentation

## System Overview

SPDF is a secure document distribution system consisting of three main components:

1. **SPDF Server** - FastAPI backend for document management
2. **SPDF Viewer** - Tauri desktop application for viewing
3. **SPDF CLI** - Command-line tool for operations

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SPDF ECOSYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────┐                         ┌────────────────┐             │
│   │  Admin Portal  │                         │   End User     │             │
│   │  (Web Browser) │                         │   (Desktop)    │             │
│   └───────┬────────┘                         └───────┬────────┘             │
│           │ HTTPS                                    │ HTTPS               │
│           ▼                                          ▼                      │
│   ┌───────────────────────────────────────────────────────────┐            │
│   │                    SPDF Server                             │            │
│   │                    (FastAPI)                               │            │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │            │
│   │   │   Routes    │  │   Crypto    │  │     API     │       │            │
│   │   │  • auth     │  │  • keys     │  │  • license  │       │            │
│   │   │  • admin    │  │  • encrypt  │  │  • device   │       │            │
│   │   │  • docs     │  │  • decrypt  │  │  • files    │       │            │
│   │   └─────────────┘  └─────────────┘  └─────────────┘       │            │
│   │                           │                                │            │
│   │   ┌───────────────────────┴────────────────────────┐      │            │
│   │   │              SQLite Database                    │      │            │
│   │   │  • Users • Documents • Licenses • Devices      │      │            │
│   │   └─────────────────────────────────────────────────┘      │            │
│   └───────────────────────────────────────────────────────────┘            │
│           │                                          │                      │
│           │ .spdf files                              │ k_doc                │
│           ▼                                          │                      │
│   ┌────────────────┐                                │                      │
│   │  SPDF Files    │─────────────────────────────────                      │
│   │  (Encrypted)   │                                 ▼                      │
│   └────────────────┘                         ┌───────────────────┐         │
│                                              │   SPDF Viewer     │         │
│                                              │   (Tauri/Rust)    │         │
│                                              │   ┌───────────┐   │         │
│                                              │   │ PDF.js    │   │         │
│                                              │   │ Renderer  │   │         │
│                                              │   └───────────┘   │         │
│                                              └───────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Document Upload Flow

```
                    ┌─────────────┐
                    │  Admin      │
                    │  uploads    │
                    │  PDF        │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  1. Sanitize PDF       │
              │  (Remove JS, forms)    │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  2. Generate k_doc     │
              │  (32-byte random)      │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  3. Encrypt PDF        │
              │  (AES-256-GCM)         │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  4. Wrap k_doc         │
              │  (AES-KW w/ K_master)  │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  5. Sign file          │
              │  (Ed25519)             │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  6. Store              │
              │  • .spdf file          │
              │  • wrapped key in DB   │
              └────────────────────────┘
```

### Document Viewing Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Open     │     │  2. Parse    │     │  3. Verify   │
│  .spdf file  │ ──▶ │  SPDF header │ ──▶ │  signature   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  6. Render   │     │  5. Decrypt  │     │  4. Validate │
│  PDF         │ ◀── │  content     │ ◀── │  license     │
│  (PDF.js)    │     │  (AES-GCM)   │     │  + device    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  │ HTTP
                                                  ▼
                                          ┌──────────────┐
                                          │  SPDF Server │
                                          │  returns     │
                                          │  k_doc       │
                                          └──────────────┘
```

## Module Architecture

### Server Modules

```
spdf-server/
├── main.py                # FastAPI application entry
├── config.py              # Configuration management
├── database.py            # SQLAlchemy database setup
├── models.py              # ORM models
│
├── crypto/                # Cryptographic operations
│   ├── __init__.py
│   ├── keys.py            # Key generation, wrapping
│   ├── encrypt.py         # SPDF file creation
│   ├── decrypt.py         # SPDF parsing, decryption
│   ├── signature.py       # Ed25519 operations
│   └── format.py          # Format constants
│
├── api/                   # REST API endpoints
│   ├── __init__.py
│   ├── license.py         # License validation
│   ├── device.py          # Device fingerprinting
│   └── files.py           # File upload/conversion
│
├── routes/                # Legacy routes (existing)
│   ├── auth.py
│   ├── admin.py
│   └── ...
│
├── tests/                 # Pytest test suite
│   ├── conftest.py
│   ├── test_encryption.py
│   ├── test_signatures.py
│   └── ...
│
└── static/                # Admin dashboard
    ├── admin.html
    └── login.html
```

### Viewer Modules

```
spdf-viewer-desktop/
├── src/                   # Frontend (TypeScript)
│   ├── main.ts
│   └── ...
│
└── src-tauri/src/         # Backend (Rust)
    ├── main.rs            # Tauri entry point
    ├── lib.rs             # Module exports
    ├── spdf_parser.rs     # SPDF file parsing
    ├── decrypt.rs         # AES-GCM decryption
    ├── verify.rs          # Ed25519 verification
    ├── device_id.rs       # Hardware fingerprinting
    └── auth.rs            # License authentication
```

## Database Schema

```
┌─────────────────┐       ┌─────────────────┐
│     users       │       │   documents     │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ email           │       │ doc_id (unique) │
│ password_hash   │       │ org_id          │
│ org_id          │       │ title           │
│ created_at      │       │ spdf_path       │
└────────┬────────┘       │ created_at      │
         │                └────────┬────────┘
         │                         │
         │    ┌────────────────────┘
         │    │
         ▼    ▼
┌─────────────────────────────┐
│          licenses           │
├─────────────────────────────┤
│ id (PK)                     │
│ user_id (FK -> users)       │
│ doc_id (FK -> documents)    │
│ license_key (unique)        │
│ max_devices                 │
│ expires_at                  │
│ created_at                  │
└─────────────────────────────┘
         │
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│    devices      │      │  document_keys  │
├─────────────────┤      ├─────────────────┤
│ id (PK)         │      │ id (PK)         │
│ user_id (FK)    │      │ doc_id (FK)     │
│ device_id       │      │ k_doc_encrypted │
│ device_hash     │      │ created_at      │
│ device_name     │      └─────────────────┘
│ registered_at   │
│ last_seen       │
└─────────────────┘
```

## API Endpoints

### License API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/license/validate` | Validate license + device |
| POST | `/api/license/create` | Create new license (admin) |
| POST | `/api/license/revoke` | Revoke license (admin) |
| GET | `/api/license/status/{key}` | Get license status |
| GET | `/api/license/list` | List all licenses (admin) |

### Device API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/device/fingerprint` | Generate device hash |
| POST | `/api/device/register` | Register device for license |
| POST | `/api/device/revoke` | Revoke device access |
| POST | `/api/device/validate` | Validate device hash |

### Files API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/files/upload` | Upload PDF |
| POST | `/api/files/convert` | Convert to SPDF |
| POST | `/api/files/convert-direct` | Upload + convert |
| GET | `/api/files/download/{id}` | Download SPDF |
| GET | `/api/files/info/{id}` | Get file metadata |
| DELETE | `/api/files/{id}` | Delete file (admin) |

## Security Architecture

### Key Management

```
┌─────────────────────────────────────────────────────────────┐
│                    Key Hierarchy                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │  K_master (Environment Variable)          │               │
│  │  • 256-bit AES key                        │               │
│  │  • Never leaves server                    │               │
│  │  • Used only for key wrapping             │               │
│  └────────────────────┬─────────────────────┘               │
│                       │                                      │
│                       │ AES-KW (RFC 3394)                   │
│                       ▼                                      │
│  ┌──────────────────────────────────────────┐               │
│  │  Wrapped k_doc (stored in DB)             │               │
│  │  • 40 bytes (32 + 8 padding)              │               │
│  │  • One per document                       │               │
│  └────────────────────┬─────────────────────┘               │
│                       │                                      │
│                       │ Unwrap on valid license              │
│                       ▼                                      │
│  ┌──────────────────────────────────────────┐               │
│  │  k_doc (returned to viewer)               │               │
│  │  • 256-bit AES-GCM key                    │               │
│  │  • Unique per document                    │               │
│  │  • Used to decrypt SPDF content           │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌──────────┐                              ┌──────────┐
│  Viewer  │                              │  Server  │
└────┬─────┘                              └────┬─────┘
     │                                         │
     │  1. Open .spdf file                     │
     │  2. Parse header, get server_url        │
     │                                         │
     │  3. Generate device_hash                │
     │                                         │
     │  4. POST /api/license/validate          │
     │  {license_key, device_hash, doc_id}     │
     │────────────────────────────────────────▶│
     │                                         │
     │                                         │  5. Validate license
     │                                         │  6. Check device limit
     │                                         │  7. Unwrap k_doc
     │                                         │
     │  8. Response {doc_key, public_key}      │
     │◀────────────────────────────────────────│
     │                                         │
     │  9. Verify signature with public_key    │
     │  10. Decrypt content with doc_key       │
     │  11. Render PDF                         │
     │                                         │
```

## Deployment Architecture

### Production Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Environment                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │  Load       │     │  SPDF       │     │  SPDF       │   │
│  │  Balancer   │────▶│  Server 1   │     │  Server 2   │   │
│  │  (HTTPS)    │     │             │     │             │   │
│  └─────────────┘     └──────┬──────┘     └──────┬──────┘   │
│                             │                   │           │
│                             ▼                   ▼           │
│                      ┌─────────────────────────────┐        │
│                      │      PostgreSQL / MySQL     │        │
│                      │      (Primary Database)     │        │
│                      └─────────────────────────────┘        │
│                                                              │
│  ┌─────────────┐     ┌─────────────┐                        │
│  │   Redis     │     │  Secrets    │                        │
│  │   (Rate     │     │  Manager    │                        │
│  │   Limiting) │     │  (K_master) │                        │
│  └─────────────┘     └─────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SPDF_MASTER_KEY` | Master encryption key (64 hex) | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `REDIS_URL` | Redis URL for rate limiting | No |
| `SECRET_KEY` | Session signing key | Yes |
| `DEBUG` | Enable debug mode | No |

## Performance Considerations

### Encryption Performance

- PDF sanitization: ~100ms per MB
- AES-GCM encryption: ~10ms per MB
- Ed25519 signing: ~1ms per signature

### Recommended Limits

- Max file size: 100 MB
- Max concurrent uploads: 10
- Rate limit: 20 requests/min/IP
