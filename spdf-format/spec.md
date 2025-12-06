# SPDF File Format Specification v1.0

## Overview

SPDF (Secure Portable Document Format) is a secure document container format that provides:
- **AES-256-GCM** authenticated encryption
- **Ed25519** digital signatures
- **License-based** access control
- **Device binding** for DRM protection

## File Structure

```
+-------------------+
|     MAGIC (4B)    |  "SPDF"
+-------------------+
|   VERSION (1B)    |  0x01
+-------------------+
|   FLAGS (2B)      |  Feature flags
+-------------------+
| HEADER_LEN (4B)   |  Big-endian uint32
+-------------------+
|   HEADER (JSON)   |  Variable length
+-------------------+
| WRAPPED_KEY (48B) |  AES-KW wrapped k_doc
+-------------------+
|  NONCE (12B)      |  AES-GCM nonce
+-------------------+
|  CIPHERTEXT       |  Encrypted PDF
+-------------------+
|  AUTH_TAG (16B)   |  GCM authentication tag
+-------------------+
|  SIGNATURE (64B)  |  Ed25519 signature
+-------------------+
```

## Field Specifications

### Magic Bytes (4 bytes)
- **Value**: `0x53 0x50 0x44 0x46` ("SPDF")
- **Purpose**: File type identification

### Version (1 byte)
- **Value**: `0x01` for v1.0
- **Purpose**: Format versioning for backward compatibility

### Flags (2 bytes, big-endian)
```
Bit 0: DEVICE_BINDING_REQUIRED
Bit 1: OFFLINE_ALLOWED
Bit 2: PRINT_ALLOWED
Bit 3: COPY_ALLOWED
Bit 4: WATERMARK_ENABLED
Bit 5-15: Reserved (must be 0)
```

### Header Length (4 bytes, big-endian)
- **Range**: 64 - 65535 bytes
- **Purpose**: Length of JSON header

### Header (JSON, UTF-8)
```json
{
  "spdf_version": "1.0",
  "doc_id": "DOC-UUID",
  "org_id": "ORG-UUID",
  "title": "Document Title",
  "server_url": "https://api.example.com",
  "created_at": "2025-12-06T00:00:00Z",
  "public_key": "-----BEGIN PUBLIC KEY-----...",
  "permissions": {
    "allow_print": false,
    "allow_copy": false,
    "max_devices": 2,
    "offline_days": 7
  },
  "watermark": {
    "enabled": true,
    "text": "{{user_email}} | {{device_id}}"
  },
  "metadata": {
    "author": "Optional Author",
    "pages": 42,
    "created_by": "admin@example.com"
  }
}
```

### Wrapped Key (48 bytes)
- **Algorithm**: AES-256-KW (RFC 3394)
- **Input**: 32-byte k_doc (document key)
- **Wrapping Key**: K_master (server-side only)
- **Output**: 40-byte wrapped key + 8-byte IV

### Nonce (12 bytes)
- **Algorithm**: Cryptographically secure random
- **Purpose**: AES-GCM initialization vector
- **Uniqueness**: MUST be unique per encryption

### Ciphertext (variable length)
- **Algorithm**: AES-256-GCM
- **Input**: Sanitized PDF bytes
- **Key**: k_doc (32 bytes)

### Authentication Tag (16 bytes)
- **Algorithm**: AES-GCM tag
- **Purpose**: Integrity verification
- **Validation**: MUST be verified before decryption

### Signature (64 bytes)
- **Algorithm**: Ed25519
- **Signed Data**: SHA-256(MAGIC || VERSION || FLAGS || HEADER_LEN || HEADER || WRAPPED_KEY || NONCE || CIPHERTEXT || AUTH_TAG)
- **Purpose**: Tamper detection

## Cryptographic Requirements

### Key Generation
- **K_master**: 256-bit, generated via `os.urandom(32)` or equivalent CSPRNG
- **k_doc**: 256-bit, unique per document
- **Ed25519 keys**: Generated per organization

### Encryption Process
1. Sanitize PDF (remove JavaScript, embedded files)
2. Generate random k_doc (32 bytes)
3. Generate random nonce (12 bytes)
4. Encrypt: `ciphertext, tag = AES-GCM(k_doc, nonce, pdf_bytes)`
5. Wrap key: `wrapped_key = AES-KW(K_master, k_doc)`
6. Build unsigned data
7. Sign: `signature = Ed25519.sign(private_key, SHA256(unsigned_data))`

### Decryption Process
1. Parse file structure
2. Verify signature with public key
3. Request k_doc from server (with license + device validation)
4. Server unwraps: `k_doc = AES-KW.unwrap(K_master, wrapped_key)`
5. Decrypt: `pdf_bytes = AES-GCM.decrypt(k_doc, nonce, ciphertext, tag)`
6. Render PDF

## Security Considerations

### Threat Model
- **Attacker Goal**: Access PDF without valid license
- **Protected Against**:
  - File modification (signature verification)
  - Key extraction (server-side key storage)
  - Device cloning (device fingerprinting)
  - Brute-force (rate limiting)

### Known Limitations
- **Client trust**: Viewer app integrity not cryptographically enforced
- **Memory attacks**: Decrypted content in memory is vulnerable
- **Screenshots**: Cannot prevent screen capture

## Version History

| Version | Date       | Changes                          |
|---------|------------|----------------------------------|
| 1.0     | 2025-12-06 | Initial specification            |

## References

- [AES-GCM (NIST SP 800-38D)](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [AES-KW (RFC 3394)](https://www.rfc-editor.org/rfc/rfc3394)
- [Ed25519 (RFC 8032)](https://www.rfc-editor.org/rfc/rfc8032)
