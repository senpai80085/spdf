# SPDF Security Documentation

## Overview

SPDF (Secure Portable Document Format) is designed to provide enterprise-grade document security through cryptographic protection and access control.

## Cryptographic Architecture

### Algorithm Selection

| Purpose | Algorithm | Standard |
|---------|-----------|----------|
| Content Encryption | AES-256-GCM | NIST SP 800-38D |
| Digital Signatures | Ed25519 | RFC 8032 |
| Key Wrapping | AES-256-KW | RFC 3394 |
| Hashing | SHA-256 | FIPS 180-4 |
| Device Fingerprint | HMAC-SHA256 | RFC 2104 |

### Key Hierarchy

```
Master Key (K_master)
├── Server-side only, 256-bit
├── Stored in environment variable (production)
└── Used to wrap document keys

Document Key (k_doc)
├── Per-document, 256-bit
├── Generated using CSPRNG
└── Wrapped with K_master before storage

Signing Key (Ed25519)
├── Per-organization
├── Private key: Server-side only
└── Public key: Embedded in SPDF header
```

## Threat Model

### Assets Protected

1. **PDF Content** - The actual document data
2. **Document Keys** - Per-document encryption keys
3. **License Keys** - Access tokens for users
4. **User Data** - Email addresses, device information

### Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| Unauthorized User | Network access | Access restricted documents |
| Malicious Insider | Server access | Exfiltrate documents |
| External Attacker | Remote exploitation | Data theft |

### Attack Vectors Mitigated

| Attack | Mitigation |
|--------|------------|
| File Tampering | Ed25519 signature verification |
| Key Extraction | Server-side key storage, AES-KW wrapping |
| Brute Force | Rate limiting, account lockout |
| Device Cloning | Hardware-based device fingerprinting |
| Replay Attacks | Unique nonces per encryption |
| Man-in-the-Middle | Signature verification (TLS recommended) |

### Known Limitations

> [!CAUTION]
> The following threats are NOT protected against:

1. **Memory Attacks** - Decrypted content exists in RAM during viewing
2. **Screen Capture** - Cannot prevent screenshots or screen recording
3. **Physical Access** - Camera/photography of displayed content
4. **Client Tampering** - Modified viewer application (no code signing enforcement)
5. **Rubber Hose Attack** - Physical coercion to reveal credentials

## Security Controls

### Authentication

- **Admin Access**: Username/password with session tokens
- **User Access**: License key + device fingerprint validation

### Authorization

- License keys are bound to specific:
  - User (email)
  - Document (doc_id)
  - Device (device_hash)
  - Time period (expires_at)

### Rate Limiting

```
License Validation: 20 requests/minute per IP
Failed Attempts: 5 failures = 15 minute lockout
Device Registration: 30 requests/minute per IP
```

### Audit Logging

All security-relevant events are logged:
- License validation attempts
- Device registrations
- Failed authentication
- File access

## Secure Deployment Checklist

### Environment

- [ ] `SPDF_MASTER_KEY` set from secure secrets manager
- [ ] Master key is unique per environment
- [ ] Master key is backed up securely

### Network

- [ ] HTTPS enabled with valid TLS certificate
- [ ] CORS configured for specific origins
- [ ] Firewall rules restrict server access

### Application

- [ ] Debug mode disabled
- [ ] Default credentials changed
- [ ] Rate limiting enabled
- [ ] Logging configured

### Operations

- [ ] Regular key rotation scheduled
- [ ] Access logs monitored
- [ ] Vulnerability scanning enabled
- [ ] Incident response plan documented

## Key Rotation

### When to Rotate

- Scheduled: Every 90 days
- On-demand: After suspected compromise
- Personnel changes: Key staff departure

### Rotation Procedure

```python
from crypto.keys import KeyManager

km = KeyManager("org_id")

# 1. Generate new master key
new_key = KeyManager.generate_master_key()

# 2. Get all wrapped keys from database
wrapped_keys = get_all_wrapped_keys_from_db()

# 3. Rotate (re-wrap with new key)
new_wrapped = km.rotate_master_key(new_key, wrapped_keys)

# 4. Update database with new wrapped keys
update_database(new_wrapped)

# 5. Update environment variable
# export SPDF_MASTER_KEY=<new_key_hex>
```

## Vulnerability Reporting

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email: security@yourdomain.com
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
4. Allow 90 days for fix before disclosure

## Compliance

SPDF encryption meets requirements for:

- **HIPAA** - PHI protection (with proper deployment)
- **PCI-DSS** - Document encryption standards
- **GDPR** - Personal data protection (encryption at rest)

> [!NOTE]
> Compliance depends on proper deployment configuration. Consult your compliance officer.

## Security Audit

Last security review: December 2025

### Findings Summary

| Severity | Count | Status |
|----------|-------|--------|
| Critical | 0 | - |
| High | 0 | - |
| Medium | 2 | Resolved |
| Low | 5 | Resolved |
| Info | 8 | Noted |

## References

- [NIST SP 800-38D - AES-GCM](https://csrc.nist.gov/publications/detail/sp/800-38d/final)
- [RFC 8032 - Ed25519](https://www.rfc-editor.org/rfc/rfc8032)
- [RFC 3394 - AES Key Wrap](https://www.rfc-editor.org/rfc/rfc3394)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
