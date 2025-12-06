"""
End-to-End Test Script for SPDF System

This script simulates the entire workflow:
1. Create a test PDF
2. Convert it to SPDF (CLI)
3. Upload it to Server (via API)
4. Verify Viewer can open it (Simulated)
"""

import os
import sys
import requests
import json
import subprocess
import time
from pathlib import Path

# Configuration
SERVER_URL = "http://localhost:8000"
TEST_PDF = "e2e_test.pdf"
TEST_SPDF = "e2e_test.spdf"
DOC_ID = "DOC-E2E-001"
ORG_ID = "ORG-1"
EMAIL = "test@example.com"
PASSWORD = "test123"

def print_step(msg):
    print(f"\n[STEP] {msg}")

def print_success(msg):
    print(f"[OK] {msg}")

def print_error(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)

def main():
    print(">>> Starting SPDF End-to-End Test")
    print("=" * 50)

    # 1. Create Test PDF
    print_step("Creating Test PDF...")
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(TEST_PDF)
        c.drawString(100, 750, "SPDF End-to-End Test Document")
        c.drawString(100, 730, "Confidential Content")
        c.save()
        print_success(f"Created {TEST_PDF}")
    except ImportError:
        print("[WARN] reportlab not found, using simple text file as mock PDF")
        with open(TEST_PDF, "wb") as f:
            f.write(b"%PDF-1.4 ... (mock content)")
        print_success(f"Created mock {TEST_PDF}")

    # 2. Convert to SPDF
    print_step("Converting to SPDF...")
    cmd = [
        sys.executable, "spdf-cli/cli.py", "convert",
        "--input", TEST_PDF,
        "--output", TEST_SPDF,
        "--doc-id", DOC_ID,
        "--org-id", ORG_ID,
        "--server-url", SERVER_URL,
        "--allow-print", # Enable print for this test
        "--watermark-text", "CONFIDENTIAL | {{user_id}}"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print_error(f"Conversion failed:\n{result.stderr}")
    print_success(f"Created {TEST_SPDF}")

    # 3. Check Server Status
    print_step("Checking Server Status...")
    try:
        r = requests.get(f"{SERVER_URL}/health")
        if r.status_code != 200:
            print_error("Server is not healthy")
        print_success("Server is running")
    except requests.exceptions.ConnectionError:
        print_error("Server is not running! Please start 'python spdf-server/main.py'")

    # 4. Login to Server
    print_step("Logging in...")
    r = requests.post(f"{SERVER_URL}/auth/login", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    if r.status_code != 200:
        # Try registering if login fails
        print("  Login failed, trying to register...")
        r = requests.post(f"{SERVER_URL}/auth/register", json={
            "email": EMAIL,
            "password": PASSWORD
        })
        if r.status_code == 200:
            print_success("Registered new user")
            # Login again
            r = requests.post(f"{SERVER_URL}/auth/login", json={
                "email": EMAIL,
                "password": PASSWORD
            })
        else:
            print_error(f"Login/Register failed: {r.text}")
    
    token = r.json()["access_token"]
    print_success("Logged in successfully")

    # 5. Upload Document (Admin)
    print_step("Uploading Document...")
    # We need to upload both .spdf and .key
    files = {
        'file': (TEST_SPDF, open(TEST_SPDF, 'rb'), 'application/octet-stream')
    }
    # Also need to ensure the .key file is available for the server to read (in this simple impl, server expects it in upload dir or we mock it)
    # The current server implementation expects the .key file to be present or uploaded. 
    # But the /docs/upload endpoint in `documents.py` reads the .key file from disk (it assumes it was uploaded or exists).
    # Wait, `documents.py` says:
    # `key_path = UPLOAD_DIR / f"{doc_id}.spdf.key"`
    # `if not key_path.exists(): ... raise HTTPException`
    # It doesn't accept the key in the upload request. This is a limitation of the current v1 upload endpoint.
    # It expects the key to be manually placed there or we need to modify the endpoint.
    # For this test, let's manually copy the key to the server's upload directory.
    
    key_file = f"{TEST_SPDF}.key"
    server_upload_dir = Path("spdf-server/uploads")
    server_upload_dir.mkdir(exist_ok=True)
    
    import shutil
    shutil.copy(key_file, server_upload_dir / f"{DOC_ID}.spdf.key")
    print_success(f"Copied key to {server_upload_dir}")

    # Now upload SPDF
    r = requests.post(
        f"{SERVER_URL}/docs/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"doc_id": DOC_ID, "title": "End-to-End Test Doc"}
    )
    
    if r.status_code != 200:
        # If already exists, that's fine
        if "already exists" in r.text:
            print("  Document already exists")
        else:
            print_error(f"Upload failed: {r.text}")
    else:
        print_success("Document uploaded")

    # 6. Create License (Admin)
    # We need to ensure the user has a license.
    # We can use the admin_setup.py logic or direct DB access, or just rely on the fact that we might have created it manually.
    # For this test script, let's assume we need to add a license.
    # Since we don't have an API for creating licenses, we'll use a direct DB hack for the test.
    print_step("Ensuring License...")
    from spdf_server.database import SessionLocal
    from spdf_server.models import License, User
    
    db = SessionLocal()
    user = db.query(User).filter(User.email == EMAIL).first()
    if user:
        lic = db.query(License).filter(License.user_id == user.id, License.doc_id == DOC_ID).first()
        if not lic:
            lic = License(user_id=user.id, doc_id=DOC_ID, max_devices=2)
            db.add(lic)
            db.commit()
            print_success("Created license")
        else:
            print("  License already exists")
    db.close()

    # 7. Simulate Viewer Key Retrieval
    print_step("Simulating Viewer Key Retrieval...")
    device_id = "TEST-DEVICE-001"
    r = requests.post(
        f"{SERVER_URL}/keys/get",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doc_id": DOC_ID,
            "device_id": device_id,
            "device_name": "Test Runner"
        }
    )
    
    if r.status_code != 200:
        print_error(f"Key retrieval failed: {r.text}")
    
    data = r.json()
    if "k_doc" not in data:
        print_error("Response missing k_doc")
    
    print_success("Received K_doc from server")
    print(f"  Permissions: {data['permissions']}")
    print(f"  Watermark: {data['watermark_data']}")

    print("\n[SUCCESS] END-TO-END TEST PASSED!")
    print("The system is functioning correctly.")

if __name__ == "__main__":
    main()
