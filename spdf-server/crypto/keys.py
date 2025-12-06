"""
SPDF Cryptographic Key Management Module

This module provides secure key generation, wrapping, and rotation
functionality for the SPDF secure document system.
"""

import os
import secrets
import hashlib
import logging
from typing import Optional, Tuple
from pathlib import Path
from base64 import b64encode, b64decode
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.keywrap import aes_key_wrap, aes_key_unwrap
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidKey

logger = logging.getLogger(__name__)

# Constants
MASTER_KEY_LENGTH = 32  # 256 bits
DOC_KEY_LENGTH = 32     # 256 bits
WRAPPED_KEY_LENGTH = 40 # AES-KW adds 8 bytes

# Environment variable name for master key
MASTER_KEY_ENV = "SPDF_MASTER_KEY"


class KeyManagementError(Exception):
    """Raised when key management operations fail."""
    pass


class KeyManager:
    """
    Manages cryptographic keys for SPDF system.
    
    Supports:
    - Master key loading from environment
    - Document key generation
    - AES-KW key wrapping/unwrapping
    - Ed25519 signing key management
    - Key rotation
    """
    
    def __init__(self, org_id: str = "default"):
        self.org_id = org_id
        self._master_key: Optional[bytes] = None
        self._signing_key: Optional[Ed25519PrivateKey] = None
        self._public_key: Optional[Ed25519PublicKey] = None
        self._keys_dir = Path(__file__).parent.parent / ".keys"
        self._keys_dir.mkdir(exist_ok=True)
        
    def _load_master_key(self) -> bytes:
        """Load master key from environment variable."""
        key_hex = os.environ.get(MASTER_KEY_ENV)
        
        if key_hex:
            try:
                key = bytes.fromhex(key_hex)
                if len(key) != MASTER_KEY_LENGTH:
                    raise KeyManagementError(
                        f"Master key must be {MASTER_KEY_LENGTH} bytes, got {len(key)}"
                    )
                return key
            except ValueError as e:
                raise KeyManagementError(f"Invalid master key hex: {e}")
        
        # Fallback: Load from file (development only)
        master_file = self._keys_dir / ".k_master"
        if master_file.exists():
            key = master_file.read_bytes()
            if len(key) == MASTER_KEY_LENGTH:
                logger.warning("Using master key from file - NOT recommended for production")
                return key
        
        # Generate new master key if none exists
        logger.warning("No master key found - generating new one")
        key = self.generate_master_key()
        master_file.write_bytes(key)
        return key
    
    @property
    def master_key(self) -> bytes:
        """Get the master key, loading if necessary."""
        if self._master_key is None:
            self._master_key = self._load_master_key()
        return self._master_key
    
    @staticmethod
    def generate_master_key() -> bytes:
        """Generate a new master key using secure randomness."""
        return secrets.token_bytes(MASTER_KEY_LENGTH)
    
    @staticmethod
    def generate_doc_key() -> bytes:
        """Generate a new document encryption key."""
        return secrets.token_bytes(DOC_KEY_LENGTH)
    
    def wrap_key(self, doc_key: bytes) -> bytes:
        """
        Wrap a document key using the master key (AES-KW).
        
        Args:
            doc_key: 32-byte document encryption key
            
        Returns:
            40-byte wrapped key
        """
        if len(doc_key) != DOC_KEY_LENGTH:
            raise KeyManagementError(f"Document key must be {DOC_KEY_LENGTH} bytes")
        
        try:
            wrapped = aes_key_wrap(self.master_key, doc_key)
            return wrapped
        except Exception as e:
            raise KeyManagementError(f"Key wrapping failed: {e}")
    
    def unwrap_key(self, wrapped_key: bytes) -> bytes:
        """
        Unwrap a document key using the master key.
        
        Args:
            wrapped_key: 40-byte wrapped key
            
        Returns:
            32-byte document encryption key
        """
        if len(wrapped_key) != WRAPPED_KEY_LENGTH:
            raise KeyManagementError(f"Wrapped key must be {WRAPPED_KEY_LENGTH} bytes")
        
        try:
            doc_key = aes_key_unwrap(self.master_key, wrapped_key)
            return doc_key
        except InvalidKey:
            raise KeyManagementError("Key unwrapping failed - invalid master key or corrupted wrapped key")
        except Exception as e:
            raise KeyManagementError(f"Key unwrapping failed: {e}")
    
    def _get_signing_key_path(self) -> Path:
        """Get path to organization's signing key."""
        return self._keys_dir / f"{self.org_id}_signing.key"
    
    def _get_public_key_path(self) -> Path:
        """Get path to organization's public key."""
        return self._keys_dir / f"{self.org_id}_public.pem"
    
    def get_signing_key(self) -> Ed25519PrivateKey:
        """
        Get or generate the Ed25519 signing key for this organization.
        """
        if self._signing_key is not None:
            return self._signing_key
        
        key_path = self._get_signing_key_path()
        
        if key_path.exists():
            # Load existing key
            key_data = key_path.read_bytes()
            self._signing_key = serialization.load_pem_private_key(key_data, password=None)
        else:
            # Generate new key pair
            self._signing_key = Ed25519PrivateKey.generate()
            
            # Save private key
            key_pem = self._signing_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            key_path.write_bytes(key_pem)
            
            # Save public key
            public_pem = self._signing_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            self._get_public_key_path().write_bytes(public_pem)
            
            logger.info(f"Generated new signing key pair for org: {self.org_id}")
        
        self._public_key = self._signing_key.public_key()
        return self._signing_key
    
    def get_public_key(self) -> Ed25519PublicKey:
        """Get the public key for signature verification."""
        if self._public_key is None:
            self.get_signing_key()  # This will also set _public_key
        return self._public_key
    
    def get_public_key_pem(self) -> str:
        """Get the public key in PEM format."""
        public_key = self.get_public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def rotate_master_key(self, new_master_key: bytes, wrapped_keys: list[bytes]) -> list[bytes]:
        """
        Rotate the master key by re-wrapping all document keys.
        
        Args:
            new_master_key: The new master key (32 bytes)
            wrapped_keys: List of wrapped document keys
            
        Returns:
            List of re-wrapped keys using new master key
        """
        if len(new_master_key) != MASTER_KEY_LENGTH:
            raise KeyManagementError(f"New master key must be {MASTER_KEY_LENGTH} bytes")
        
        # Unwrap all keys with old master
        doc_keys = []
        for wrapped in wrapped_keys:
            doc_key = self.unwrap_key(wrapped)
            doc_keys.append(doc_key)
        
        # Update master key
        old_master = self._master_key
        self._master_key = new_master_key
        
        # Re-wrap all keys with new master
        new_wrapped = []
        try:
            for doc_key in doc_keys:
                new_wrapped.append(self.wrap_key(doc_key))
        except Exception as e:
            # Rollback on failure
            self._master_key = old_master
            raise KeyManagementError(f"Key rotation failed: {e}")
        
        return new_wrapped


def generate_device_salt() -> bytes:
    """Generate a salt for device fingerprinting."""
    return secrets.token_bytes(16)


def hash_device_info(cpu_id: str, mac_address: str, os_info: str, salt: bytes) -> str:
    """
    Create a deterministic device hash from hardware info.
    
    Args:
        cpu_id: CPU identifier
        mac_address: Primary MAC address
        os_info: OS version string
        salt: Random salt for this installation
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    data = f"{cpu_id}:{mac_address}:{os_info}".encode('utf-8')
    return hashlib.sha256(salt + data).hexdigest()


# Global key manager instance (for backward compatibility)
_default_key_manager: Optional[KeyManager] = None


def get_key_manager(org_id: str = "default") -> KeyManager:
    """Get or create a key manager for the given organization."""
    global _default_key_manager
    if _default_key_manager is None or _default_key_manager.org_id != org_id:
        _default_key_manager = KeyManager(org_id)
    return _default_key_manager
