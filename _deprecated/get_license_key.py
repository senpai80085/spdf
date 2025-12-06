import sys
import os
# Add spdf-server to path for DB access
sys.path.insert(0, 'spdf-server')
from database import SessionLocal
from models import License, User

def main():
    db = SessionLocal()
    email = "viewer@test.com"
    doc_id = "DOC-TEST-SUITE-001"
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print("User not found")
        return

    lic = db.query(License).filter(License.user_id == user.id, License.doc_id == doc_id).first()
    if not lic:
        print("License not found")
        return

    print(f"LICENSE_KEY: {lic.license_key}")
    
if __name__ == "__main__":
    main()
