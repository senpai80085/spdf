"""
Admin utility script for SPDF Server

Create test users and licenses for development/testing.
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, License, Document
from routes.auth import get_password_hash

# Create tables
Base.metadata.create_all(bind=engine)


def create_test_user(db: Session):
    """Create a test user."""
    email = "test@example.com"
    password = "test123"
    
    # Check if exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"✓ Test user already exists: {email}")
        return existing_user
    
    # Create user
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        org_id="ORG-1"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print(f"✓ Created test user: {email} / {password}")
    return user


def create_test_license(db: Session, user_id: int, doc_id: str):
    """Create a test license."""
    # Check if exists
    existing_license = db.query(License).filter(
        License.user_id == user_id,
        License.doc_id == doc_id
    ).first()
    
    if existing_license:
        print(f"✓ License already exists for doc: {doc_id}")
        return existing_license
    
    # Create license
    license = License(
        user_id=user_id,
        doc_id=doc_id,
        max_devices=2
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    
    print(f"✓ Created license for doc: {doc_id} (max_devices: 2)")
    return license


def main():
    db = SessionLocal()
    
    try:
        print("\n🔧 SPDF Server Admin Setup")
        print("=" * 50)
        
        # Create test user
        user = create_test_user(db)
        
        # Create test license for DOC-1
        create_test_license(db, user.id, "DOC-1")
        
        print("\n✅ Admin setup complete!")
        print("=" * 50)
        print("\nTest credentials:")
        print("  Email: test@example.com")
        print("  Password: test123")
        print("\nTest document: DOC-1")
        print("=" * 50)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
