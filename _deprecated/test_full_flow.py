import requests
import json
import os

BASE_URL = "http://localhost:8000"
EMAIL = "test@example.com"
PASSWORD = "test123"

def run_test():
    print("🚀 Starting End-to-End Test...")

    # 1. Admin Login
    print("\n1️⃣  Logging in as Admin...")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": EMAIL,
        "password": PASSWORD
    })
    if res.status_code != 200:
        print(f"❌ Login failed: {res.text}")
        return
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful")

    # 2. Upload PDF
    print("\n2️⃣  Uploading PDF...")
    files = {'file': ('test_upload.pdf', open('test_upload.pdf', 'rb'), 'application/pdf')}
    data = {
        "doc_id": "DOC-PY-TEST",
        "title": "Python Test Doc",
        "org_id": "ORG-1",
        "max_devices": 2
    }
    res = requests.post(f"{BASE_URL}/admin/convert", headers=headers, files=files, data=data)
    
    # Handle case where doc already exists
    if res.status_code == 400 and "already exists" in res.text:
        print("⚠️  Document already exists, proceeding...")
    elif res.status_code != 200:
        print(f"❌ Upload failed: {res.text}")
        return
    else:
        print("✅ Upload successful")

    # 3. Create License
    print("\n3️⃣  Creating License...")
    # First get user ID
    # res = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    # users = res.json()
    # user_id = next((u['id'] for u in users if u['email'] == EMAIL), None)
    user_id = 1 # Hardcoded for testing stability
    
    license_data = {
        "user_id": int(user_id), # Ensure int
        "doc_id": "DOC-PY-TEST",
        "max_devices": 2
    }
    print(f"DEBUG: Sending license data: {json.dumps(license_data)}")
    res = requests.post(f"{BASE_URL}/admin/licenses", headers=headers, json=license_data)
    if res.status_code != 200:
        print(f"❌ License creation failed: {res.text}")
        return
    
    license_key = res.json()["license_key"]
    print(f"✅ License created. Key: {license_key}")

    # 4. Viewer Authentication (The Real Test)
    print("\n4️⃣  Testing Viewer Authentication...")
    res = requests.post(f"{BASE_URL}/auth/login-with-key", json={
        "license_key": license_key
    })
    
    if res.status_code == 200:
        auth_data = res.json()
        print("✅ Viewer Authentication SUCCESSFUL!")
        print(f"   - Access Token: {auth_data['access_token'][:20]}...")
        print(f"   - User: {auth_data['user_email']}")
        print(f"   - Doc: {auth_data['doc_id']}")
    else:
        print(f"❌ Viewer Authentication Failed: {res.text}")

if __name__ == "__main__":
    run_test()
