import sys
import os
import shutil
from pathlib import Path

# Add spdf-format to path
sys.path.insert(0, 'spdf-format')
from spdf_format import write_spdf, generate_k_doc

# Add spdf-server to path for DB access
sys.path.insert(0, 'spdf-server')
from database import SessionLocal, Base, engine
from models import License, User, Document, DocumentKey
from routes.keys import encrypt_k_doc
from routes.auth import get_password_hash

# Configuration
EMAIL = "viewer@test.com"
PASSWORD = "test123"
DOC_ID = "DOC-TEST-SUITE-001"
ORG_ID = "ORG-TEST"

def main():
    print("🔧 Setting up SPDF Data...")
    
    # 1. Init DB
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 2. Key Setup
    k_doc = generate_k_doc()
    
    # Place key file in uploads (for server to read if needed by legacy logic, though we insert directly too)
    server_uploads = Path("spdf-server/uploads")
    server_uploads.mkdir(parents=True, exist_ok=True)
    with open(server_uploads / f"{DOC_ID}.spdf.key", "wb") as f:
        f.write(k_doc)
    
    # Encrypt for DB
    k_doc_encrypted = encrypt_k_doc(k_doc)
    
    # 3. Create SPDF File
    from cryptography.hazmat.primitives.asymmetric import ed25519
    private_key = ed25519.Ed25519PrivateKey.generate()
    write_spdf(
        str(server_uploads / f"{DOC_ID}.spdf"),
        b"TEST PDF CONTENT",
        {
            "spdf_version": "1.0", "doc_id": DOC_ID, "org_id": ORG_ID, "server_url": "http://localhost:8000",
            "permissions": {"allow_print": True, "allow_copy": True, "max_devices": 3},
            "watermark": {"enabled": True, "text": "TEST"}
        },
        k_doc,
        private_key
    )
    
    # 4. User
    user = db.query(User).filter(User.email == EMAIL).first()
    if not user:
        user = User(email=EMAIL, password_hash=get_password_hash(PASSWORD), org_id=ORG_ID)
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ User created: {user.id}")
    else:
        user.password_hash = get_password_hash(PASSWORD)
        db.commit()
        print(f"✅ User exists (updated password): {user.id}")

    # 5. Document
    doc = db.query(Document).filter(Document.doc_id == DOC_ID).first()
    if not doc:
        doc = Document(
            doc_id=DOC_ID,
            title="TestSuite Doc",
            org_id=ORG_ID,
            spdf_path=str(server_uploads / f"{DOC_ID}.spdf")
        )
        db.add(doc)
        
        doc_key = DocumentKey(doc_id=DOC_ID, k_doc_encrypted=k_doc_encrypted)
        db.add(doc_key)
        
        db.commit()
        print(f"✅ Document created: {DOC_ID}")
    else:
        print(f"✅ Document exists: {DOC_ID}")

    # 6. License
    from models import generate_license_key
    lic = db.query(License).filter(License.user_id == user.id, License.doc_id == DOC_ID).first()
    if not lic:
        lic = License(
            user_id=user.id,
            doc_id=DOC_ID,
            max_devices=5,
            license_key=generate_license_key()
        )
        db.add(lic)
        db.commit()
        db.refresh(lic)
        print(f"✅ License created: {lic.license_key}")
    else:
        if not lic.license_key:
            lic.license_key = generate_license_key()
            db.commit()
            db.refresh(lic)
            print(f"✅ License updated with key: {lic.license_key}")
        else:
            print(f"✅ License exists: {lic.license_key}")

    print("\n🎉 Setup Complete!")
    print(f"Key (Hex): {k_doc.hex()}")
    print(f"LICENSE KEY (Use this in Viewer): {lic.license_key}")
    print("Now update verify_client.py with this hex key to verify.")

if __name__ == "__main__":
    main()
