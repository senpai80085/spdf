"""
Configuration for SPDF Server
"""

import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Server configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")  # For JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Database
DATABASE_URL = "sqlite:///./spdf_server.db"

# Storage
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Master encryption key (K_master)
# In production, this should be stored securely, not in code
K_MASTER_FILE = Path(".k_master")

def get_k_master() -> bytes:
    """
    Get or generate K_master (AES-256 key for encrypting document keys).
    """
    if K_MASTER_FILE.exists():
        with open(K_MASTER_FILE, 'rb') as f:
            k_master = f.read()
            if len(k_master) != 32:
                raise ValueError("K_master file is corrupted")
            return k_master
    
    # Generate new K_master
    k_master = AESGCM.generate_key(bit_length=256)
    with open(K_MASTER_FILE, 'wb') as f:
        f.write(k_master)
    
    # Set restrictive permissions
    os.chmod(K_MASTER_FILE, 0o600)
    
    print(f"⚠️  Generated new K_master at {K_MASTER_FILE}")
    print(f"   IMPORTANT: Back up this file securely!")
    
    return k_master

K_MASTER = get_k_master()
