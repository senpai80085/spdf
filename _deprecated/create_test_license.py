"""
Quick script to create a license for testing
"""
import sys
sys.path.insert(0, 'spdf-server')

from spdf_server.database import SessionLocal
from spdf_server.models import License, User, Document
from spdf_server.crypto_utils import generate_license_key
import secrets

db = SessionLocal()

# Get the user
user = db.query(User).filter(User.email == "viewer@test.com").first()
if not user:
    print("❌ User not found. Creating...")
    from spdf_server.auth import get_password_hash
    user = User(email="viewer@test.com", hashed_password=get_password_hash("test123"), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

print(f"✅ User: {user.email} (ID: {user.id})")

# Check if document exists, if not create a placeholder
doc_id = "DOC-E2E-001"
doc = db.query(Document).filter(Document.doc_id == doc_id).first()
if not doc:
    doc = Document(
        doc_id=doc_id,
        title="Test Document",
        filename="e2e_test.spdf",
        org_id="ORG-1"
    )
    db.add(doc)
    db.commit()
    print(f"✅ Created document: {doc_id}")

# Create or get license
license = db.query(License).filter(
    License.user_id == user.id,
    License.doc_id == doc_id
).first()

if not license:
    license = License(
        user_id=user.id,
        doc_id=doc_id,
        max_devices=3
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    print(f"✅ Created license for {user.email} → {doc_id}")
else:
    print(f"✅ License already exists")

# Generate the license key
license_key = generate_license_key(user.id, doc_id)
print(f"\n🔑 LICENSE KEY: {license_key}")
print(f"\nCopy this key to use in the viewer!")

db.close()
