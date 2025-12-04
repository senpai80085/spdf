"""
SQLAlchemy Models for SPDF Server
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="user", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String, unique=True, index=True)
    device_name = Column(String)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="devices")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, index=True)
    doc_id = Column(String, unique=True, index=True)
    title = Column(String)
    spdf_path = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document_keys = relationship("DocumentKey", back_populates="document", cascade="all, delete-orphan")
    licenses = relationship("License", back_populates="document", cascade="all, delete-orphan")


class DocumentKey(Base):
    __tablename__ = "document_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, ForeignKey("documents.doc_id"))
    k_doc_encrypted = Column(LargeBinary)  # AES-256-GCM encrypted with K_master
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="document_keys")


class License(Base):
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    doc_id = Column(String, ForeignKey("documents.doc_id"))
    license_key = Column(String, unique=True, index=True)  # New: Unique license key
    max_devices = Column(Integer, default=2)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="licenses")
    document = relationship("Document", back_populates="licenses")


def generate_license_key() -> str:
    """Generate a unique license key in format SPDF-XXXX-XXXX-XXXX-XXXX"""
    import secrets
    import string
    
    chars = string.ascii_uppercase + string.digits
    parts = []
    for _ in range(4):
        part = ''.join(secrets.choice(chars) for _ in range(4))
        parts.append(part)
    
    return f"SPDF-{'-'.join(parts)}"
