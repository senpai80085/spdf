"""
SPDF Format Library v1.0

Provides utilities for creating, reading, and verifying .spdf files.

File format:
[0-3]   MAGIC       = "SPDF"                  (4 bytes)
[4]     VERSION     = 1                       (1 byte, uint8)
[5-8]   HEADER_LEN  = length of header JSON   (4 bytes, uint32, big-endian)
[9..]   HEADER_JSON = UTF-8 JSON              (HEADER_LEN bytes)
[...]   CONTENT     = AES-256-GCM ciphertext  (variable length)
[...]   SIGNATURE   = Ed25519 signature       (64 bytes)
"""

import struct
import json
import hashlib
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import os

# Constants
MAGIC = b"SPDF"
VERSION = 1
SIGNATURE_LENGTH = 64
NONCE_LENGTH = 12  # AES-GCM standard nonce length
TAG_LENGTH = 16    # AES-GCM authentication tag length


class SPDFFormatError(Exception):
    """Raised when SPDF file format is invalid."""
    pass


class SPDFSignatureError(Exception):
    """Raised when SPDF signature verification fails."""
    pass


def encrypt_pdf(pdf_bytes: bytes, k_doc: bytes) -> bytes:
    """
    Encrypt PDF bytes using AES-256-GCM.
    
    Args:
        pdf_bytes: Sanitized PDF bytes
        k_doc: 32-byte AES-256 key
    
    Returns:
        nonce || ciphertext || tag (concatenated)
    """
    if len(k_doc) != 32:
        raise ValueError("k_doc must be 32 bytes for AES-256")
    
    # Generate random nonce
    nonce = os.urandom(NONCE_LENGTH)
    
    # Encrypt
    aesgcm = AESGCM(k_doc)
    ciphertext_with_tag = aesgcm.encrypt(nonce, pdf_bytes, None)
    
    # Return nonce || ciphertext || tag
    return nonce + ciphertext_with_tag


def decrypt_pdf(content: bytes, k_doc: bytes) -> bytes:
    """
    Decrypt SPDF content using AES-256-GCM.
    
    Args:
        content: nonce || ciphertext || tag
        k_doc: 32-byte AES-256 key
    
    Returns:
        Decrypted PDF bytes
    """
    if len(k_doc) != 32:
        raise ValueError("k_doc must be 32 bytes for AES-256")
    
    if len(content) < NONCE_LENGTH + TAG_LENGTH:
        raise SPDFFormatError("Content too short to contain nonce and tag")
    
    # Extract nonce and ciphertext+tag
    nonce = content[:NONCE_LENGTH]
    ciphertext_with_tag = content[NONCE_LENGTH:]
    
    # Decrypt
    aesgcm = AESGCM(k_doc)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext
    except Exception as e:
        raise SPDFFormatError(f"Decryption failed: {e}")


def sign_spdf(data: bytes, private_key: Ed25519PrivateKey) -> bytes:
    """
    Sign SPDF data using Ed25519.
    
    Args:
        data: Data to sign (everything except signature)
        private_key: Ed25519 private key
    
    Returns:
        64-byte signature
    """
    # Hash the data first
    data_hash = hashlib.sha256(data).digest()
    
    # Sign the hash
    signature = private_key.sign(data_hash)
    return signature


def verify_spdf_signature(data: bytes, signature: bytes, public_key: Ed25519PublicKey) -> bool:
    """
    Verify SPDF signature using Ed25519.
    
    Args:
        data: Data that was signed
        signature: 64-byte signature
        public_key: Ed25519 public key
    
    Returns:
        True if signature is valid
    """
    if len(signature) != SIGNATURE_LENGTH:
        raise SPDFSignatureError(f"Signature must be {SIGNATURE_LENGTH} bytes")
    
    # Hash the data
    data_hash = hashlib.sha256(data).digest()
    
    # Verify signature
    try:
        public_key.verify(signature, data_hash)
        return True
    except Exception as e:
        raise SPDFSignatureError(f"Signature verification failed: {e}")


def write_spdf(
    output_path: str,
    pdf_bytes: bytes,
    header_dict: Dict,
    k_doc: bytes,
    private_key: Ed25519PrivateKey
) -> None:
    """
    Write a complete SPDF file.
    
    Args:
        output_path: Path to output .spdf file
        pdf_bytes: Sanitized PDF bytes
        header_dict: Header dictionary (will be JSON-encoded)
        k_doc: 32-byte AES-256 key for encryption
        private_key: Ed25519 private key for signing
    """
    # Validate inputs
    if len(k_doc) != 32:
        raise ValueError("k_doc must be 32 bytes")
    
    # Encrypt PDF content
    content = encrypt_pdf(pdf_bytes, k_doc)
    
    # Serialize header
    header_json = json.dumps(header_dict, separators=(',', ':')).encode('utf-8')
    header_len = len(header_json)
    
    # Build unsigned portion
    unsigned_data = MAGIC + struct.pack('B', VERSION) + struct.pack('>I', header_len) + header_json + content
    
    # Sign
    signature = sign_spdf(unsigned_data, private_key)
    
    # Write complete file
    with open(output_path, 'wb') as f:
        f.write(unsigned_data)
        f.write(signature)


def read_spdf(file_path: str) -> Tuple[Dict, bytes, bytes]:
    """
    Read and parse an SPDF file (without verification).
    
    Args:
        file_path: Path to .spdf file
    
    Returns:
        Tuple of (header_dict, content, signature)
    """
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Parse MAGIC
    if len(data) < 4:
        raise SPDFFormatError("File too short")
    
    magic = data[0:4]
    if magic != MAGIC:
        raise SPDFFormatError(f"Invalid magic bytes. Expected {MAGIC}, got {magic}")
    
    # Parse VERSION
    if len(data) < 5:
        raise SPDFFormatError("File too short for version")
    
    version = data[4]
    if version != VERSION:
        raise SPDFFormatError(f"Unsupported version {version}")
    
    # Parse HEADER_LEN
    if len(data) < 9:
        raise SPDFFormatError("File too short for header length")
    
    header_len = struct.unpack('>I', data[5:9])[0]
    
    # Parse HEADER_JSON
    header_start = 9
    header_end = header_start + header_len
    
    if len(data) < header_end:
        raise SPDFFormatError("File too short for header")
    
    header_json = data[header_start:header_end]
    try:
        header_dict = json.loads(header_json.decode('utf-8'))
    except Exception as e:
        raise SPDFFormatError(f"Invalid header JSON: {e}")
    
    # Extract CONTENT and SIGNATURE
    content_start = header_end
    
    if len(data) < content_start + SIGNATURE_LENGTH:
        raise SPDFFormatError("File too short for signature")
    
    # Signature is always last 64 bytes
    signature = data[-SIGNATURE_LENGTH:]
    content = data[content_start:-SIGNATURE_LENGTH]
    
    return header_dict, content, signature


def verify_and_decrypt_spdf(
    file_path: str,
    k_doc: bytes,
    public_key: Ed25519PublicKey
) -> Tuple[Dict, bytes]:
    """
    Verify signature and decrypt SPDF file.
    
    Args:
        file_path: Path to .spdf file
        k_doc: 32-byte AES-256 decryption key
        public_key: Ed25519 public key for verification
    
    Returns:
        Tuple of (header_dict, decrypted_pdf_bytes)
    
    Raises:
        SPDFSignatureError: If signature is invalid
        SPDFFormatError: If file format is invalid or decryption fails
    """
    # Read file
    header_dict, content, signature = read_spdf(file_path)
    
    # Reconstruct unsigned data for verification
    header_json = json.dumps(header_dict, separators=(',', ':')).encode('utf-8')
    header_len = len(header_json)
    unsigned_data = MAGIC + struct.pack('B', VERSION) + struct.pack('>I', header_len) + header_json + content
    
    # Verify signature
    verify_spdf_signature(unsigned_data, signature, public_key)
    
    # Decrypt content
    pdf_bytes = decrypt_pdf(content, k_doc)
    
    return header_dict, pdf_bytes


def generate_k_doc() -> bytes:
    """Generate a random 256-bit AES key."""
    return os.urandom(32)
