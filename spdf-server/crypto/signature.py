"""
SPDF Signature Module

Provides Ed25519 signature generation and verification.
"""

import hashlib
import logging
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

SIGNATURE_LENGTH = 64


class SignatureError(Exception):
    """Raised when signature operations fail."""
    pass


def sign_data(data: bytes, private_key: Ed25519PrivateKey) -> bytes:
    """
    Sign data using Ed25519.
    
    The data is first hashed with SHA-256, then signed.
    
    Args:
        data: Data to sign
        private_key: Ed25519 private key
        
    Returns:
        64-byte signature
    """
    data_hash = hashlib.sha256(data).digest()
    signature = private_key.sign(data_hash)
    return signature


def verify_signature(data: bytes, signature: bytes, public_key: Ed25519PublicKey) -> bool:
    """
    Verify Ed25519 signature.
    
    Args:
        data: Original data that was signed
        signature: 64-byte signature
        public_key: Ed25519 public key
        
    Returns:
        True if valid
        
    Raises:
        SignatureError: If verification fails
    """
    if len(signature) != SIGNATURE_LENGTH:
        raise SignatureError(f"Invalid signature length: expected {SIGNATURE_LENGTH}, got {len(signature)}")
    
    try:
        data_hash = hashlib.sha256(data).digest()
        public_key.verify(signature, data_hash)
        return True
    except Exception as e:
        raise SignatureError(f"Signature verification failed: {e}")


def verify_signature_pem(data: bytes, signature: bytes, public_key_pem: str) -> bool:
    """
    Verify signature using PEM-encoded public key.
    
    Args:
        data: Original data
        signature: 64-byte signature
        public_key_pem: PEM-encoded public key
        
    Returns:
        True if valid
    """
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        if not isinstance(public_key, Ed25519PublicKey):
            raise SignatureError("Invalid key type - expected Ed25519")
        return verify_signature(data, signature, public_key)
    except SignatureError:
        raise
    except Exception as e:
        raise SignatureError(f"Failed to parse public key: {e}")


def load_private_key_pem(pem_data: str) -> Ed25519PrivateKey:
    """Load Ed25519 private key from PEM string."""
    key = serialization.load_pem_private_key(pem_data.encode('utf-8'), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SignatureError("Invalid key type - expected Ed25519 private key")
    return key


def load_public_key_pem(pem_data: str) -> Ed25519PublicKey:
    """Load Ed25519 public key from PEM string."""
    key = serialization.load_pem_public_key(pem_data.encode('utf-8'))
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError("Invalid key type - expected Ed25519 public key")
    return key


def export_public_key_pem(public_key: Ed25519PublicKey) -> str:
    """Export public key to PEM format."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
