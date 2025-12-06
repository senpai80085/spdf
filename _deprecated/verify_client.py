import sys
import requests
import base64

SERVER_URL = "http://localhost:8000"
EMAIL = "viewer@test.com"
PASSWORD = "test123"
DOC_ID = "DOC-TEST-SUITE-001"

def main():
    print("🔍 Verifying Client Access...")
    
    # 1. Login
    s = requests.Session()
    r = s.post(f"{SERVER_URL}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code != 200:
        print(f"❌ Login failed: {r.text}")
        sys.exit(1)
    
    token = r.json()["access_token"]
    print("✅ Login successful")
    
    # 2. Get Key
    print("🔑 Requesting Key...")
    r = s.post(
        f"{SERVER_URL}/keys/get",
        headers={"Authorization": f"Bearer {token}"},
        json={"doc_id": DOC_ID, "device_id": "TEST-CLIENT", "device_name": "Verifier"}
    )
    
    if r.status_code != 200:
        print(f"❌ Key retrieval failed: {r.text}")
        sys.exit(1)
        
    data = r.json()
    k_doc_b64 = data.get("k_doc")
    license_key = data.get("license_key", "UNKNOWN") # If API returns it
    
    print(f"✅ Key received (Base64): {k_doc_b64[:10]}...")
    
    # 3. Print Instructions
    print("\n✅ VERIFICATION SUCCESSFUL")
    print("="*50)
    print(f"User Email: {EMAIL}")
    print(f"Password:   {PASSWORD}")
    # Note: The license key is needed for the Viewer prompt!
    # Does keys/get return it? Probably not.
    # But usually the user enters the LICENSE KEY to login?
    # In my viewer code, `login(..., license_key)`.
    # So I need the LICENSE KEY to give to the user.
    # setup_data.py printed it. I should grab it from there or DB.
    
if __name__ == "__main__":
    main()
