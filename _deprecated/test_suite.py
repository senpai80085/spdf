import sys
import os
import shutil
import base64
import json
import requests
import time
from pathlib import Path

# Add spdf-format to path
sys.path.insert(0, 'spdf-format')
from spdf_format import write_spdf, generate_k_doc

# Add spdf-server to path for DB access (License creation hack)
sys.path.insert(0, 'spdf-server')
from database import SessionLocal
from models import License, User

# Configuration
SERVER_URL = "http://localhost:8000"
EMAIL = "viewer@test.com"
PASSWORD = "test123"
DOC_ID = "DOC-TEST-SUITE-001"
ORG_ID = "ORG-TEST"

def log(msg, type="INFO"):
    print(f"[{type}] {msg}")

def fail(msg):
    log(msg, "ERROR")
    sys.exit(1)

def main():
    log("Starting SPDF System Verification Suite")
    
    # 1. Health Check
    try:
        r = requests.get(f"{SERVER_URL}/health")
        if r.status_code != 200:
            fail(f"Server returned {r.status_code}")
        log("Server is executing and healthy")
    except Exception as e:
        fail(f"Could not connect to server: {e}")

    # 2. Key Setup (Mock)
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    
    log("Generating test keys...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Save public key for Viewer (simulation)
    # The viewer looks in ~/.spdf/keys/{ORG_ID}_public.pem
    home = Path.home()
    keys_dir = home / ".spdf" / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(keys_dir / f"{ORG_ID}_public.pem", "wb") as f:
        f.write(pub_pem)
    log(f"Placed public key in {keys_dir}")

    # 3. Create Valid SPDF
    log("Creating test SPDF document...")
    k_doc = generate_k_doc()
    pdf_content = b"%PDF-1.4\nTest Content for SPDF Viewer\n%%EOF"
    
    header = {
        "spdf_version": "1.0",
        "doc_id": DOC_ID,
        "org_id": ORG_ID,
        "server_url": SERVER_URL,
        "created_at": "2023-01-01T00:00:00Z",
        "permissions": {"allow_print": True, "allow_copy": True, "max_devices": 3},
        "watermark": {"enabled": True, "text": "TEST WATERMARK"}
    }
    
    write_spdf("test_suite.spdf", pdf_content, header, k_doc, private_key)
    log("Created 'test_suite.spdf'")

    # 4. Upload Setup (Key Hack)
    # Server expects key file in uploads dir
    server_uploads = Path("spdf-server/uploads")
    server_uploads.mkdir(parents=True, exist_ok=True)
    with open(server_uploads / f"{DOC_ID}.spdf.key", "wb") as f:
        f.write(k_doc)
    log(f"Placed key file in {server_uploads}")

    # 5. User Registration/Login
    log(f"Authenticating user {EMAIL}...")
    s = requests.Session()
    
    # Try Login
    r = s.post(f"{SERVER_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        log("Login failed, attempting registration...")
        r = s.post(f"{SERVER_URL}/auth/register", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code != 200:
            fail(f"Registration failed: {r.text}")
        # Login again
        r = s.post(f"{SERVER_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code != 200:
            fail("Login failed after registration")
            
    token = r.json()["access_token"]
    log(f"Authenticated successfully as {EMAIL}")

    # 6. Upload Document
    log("Uploading SPDF to server...")
    with open("test_suite.spdf", "rb") as f:
        files = {"file": ("test_suite.spdf", f, "application/octet-stream")}
        # Send metadata as query params b/c server defines them as such
        params = {"doc_id": DOC_ID, "title": "TestSuite Doc", "org_id": ORG_ID}
        r = s.post(
            f"{SERVER_URL}/docs/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            params=params
        )
        if r.status_code == 200:
            log("Upload successful")
        elif "already exists" in r.text or "IntegrityError" in r.text:
            log("Document already exists (skipping upload)")
        else:
            fail(f"Upload failed: {r.text}")

    # 7. Create License (Direct DB)
    log("Ensuring valid license exists...")
    db = SessionLocal()
    # Find user ID (to be safe from DB side)
    db_user = db.query(User).filter(User.email == EMAIL).first()
    if not db_user: fail("User not found in DB")
    
    license = db.query(License).filter(License.user_id == db_user.id, License.doc_id == DOC_ID).first()
    if not license:
        license = License(user_id=db_user.id, doc_id=DOC_ID, max_devices=5)
        db.add(license)
        db.commit()
        log("Created new license")
    else:
        log("License already exists")
    db.close()

    # 8. Key Retrieval (Viewer Simulation)
    log("Attempting Key Retrieval (Viewer Simulation)...")
    device_id = "TEST-SUITE-DEVICE"
    
    r = s.post(
        f"{SERVER_URL}/keys/get",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doc_id": DOC_ID,
            "device_id": device_id,
            "device_name": "Test Suite Runner"
        }
    )
    
    if r.status_code != 200:
        fail(f"Key retrieval failed: {r.text}")
        
    data = r.json()
    if "k_doc" not in data:
        fail("Response missing 'k_doc'")
        
    k_doc_b64 = data["k_doc"]
    log(f"Received k_doc (base64): {k_doc_b64[:10]}...")
    
    # 9. Verify Key Match
    # Note: Server returns encrypted key? No, /keys/get returns the DECRYPTED key (encrypted over TLS, but raw in JSON?) 
    # Let's check routes/keys.py.
    # Actually, the logic is likely: Server stores Encrypted Key (with K_master). It decrypts it, then sends it to user.
    # Wait, does it re-encrypt it for the device? 
    # The viewer code expected: `let k_doc_bytes = base64::decode(&key_res.k_doc)`
    # And then used it directly for AES-GCM.
    # So the server sends the raw key (base64 encoded).
    
    try:
        received_key = base64.b64decode(k_doc_b64)
    except Exception as e:
        fail(f"Failed to base64 decode received key: {e}")

    if received_key == k_doc:
        log("SUCCESS: Received key matches original encryption key!")
    else:
        log(f"Original: {k_doc.hex()}")
        log(f"Received: {received_key.hex()}")
        fail("FATAL: Key mismatch! Server returned wrong key.")

    print("\n✅ SYSTEM VERIFICATION PASSED")
    print("You can now run the Viewer and open 'test_suite.spdf' with user credentials.")
    print(f"User: {EMAIL} / {PASSWORD}")

if __name__ == "__main__":
    main()
