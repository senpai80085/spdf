"""
Encryption Module Tests

Tests for AES-256-GCM encryption functionality.
"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.encrypt import (
    encrypt_pdf,
    sanitize_pdf,
    create_spdf,
    build_flags,
    FLAG_DEVICE_BINDING,
    FLAG_PRINT_ALLOWED,
    FLAG_COPY_ALLOWED,
    FLAG_WATERMARK_ENABLED
)
from crypto.keys import KeyManager


class TestEncryption:
    """Tests for encryption functions."""
    
    def test_encrypt_pdf_basic(self, sample_pdf_bytes, doc_key):
        """Test basic PDF encryption."""
        nonce, ciphertext, auth_tag = encrypt_pdf(sample_pdf_bytes, doc_key)
        
        # Check output sizes
        assert len(nonce) == 12
        assert len(auth_tag) == 16
        assert len(ciphertext) > 0
        
        # Ciphertext should be different from plaintext
        assert ciphertext != sample_pdf_bytes
    
    def test_encrypt_pdf_different_keys(self, sample_pdf_bytes):
        """Test that different keys produce different ciphertext."""
        key1 = KeyManager.generate_doc_key()
        key2 = KeyManager.generate_doc_key()
        
        _, ciphertext1, _ = encrypt_pdf(sample_pdf_bytes, key1)
        _, ciphertext2, _ = encrypt_pdf(sample_pdf_bytes, key2)
        
        assert ciphertext1 != ciphertext2
    
    def test_encrypt_pdf_different_nonces(self, sample_pdf_bytes, doc_key):
        """Test that each encryption produces different nonce."""
        nonce1, _, _ = encrypt_pdf(sample_pdf_bytes, doc_key)
        nonce2, _, _ = encrypt_pdf(sample_pdf_bytes, doc_key)
        
        assert nonce1 != nonce2
    
    def test_encrypt_pdf_invalid_key_length(self, sample_pdf_bytes):
        """Test that invalid key length raises error."""
        short_key = b"short"
        
        with pytest.raises(Exception):
            encrypt_pdf(sample_pdf_bytes, short_key)
    
    def test_encrypt_empty_content(self, doc_key):
        """Test encryption of empty content."""
        nonce, ciphertext, auth_tag = encrypt_pdf(b"", doc_key)
        
        assert len(nonce) == 12
        assert len(auth_tag) == 16
        # Empty plaintext still produces some ciphertext (just the tag)


class TestFlags:
    """Tests for flag building."""
    
    def test_build_flags_default(self):
        """Test default flags."""
        flags = build_flags()
        
        assert flags & FLAG_DEVICE_BINDING
        assert flags & FLAG_WATERMARK_ENABLED
        assert not (flags & FLAG_PRINT_ALLOWED)
        assert not (flags & FLAG_COPY_ALLOWED)
    
    def test_build_flags_all_enabled(self):
        """Test all flags enabled."""
        flags = build_flags(
            device_binding=True,
            offline_allowed=True,
            print_allowed=True,
            copy_allowed=True,
            watermark_enabled=True
        )
        
        assert flags & FLAG_DEVICE_BINDING
        assert flags & FLAG_PRINT_ALLOWED
        assert flags & FLAG_COPY_ALLOWED
        assert flags & FLAG_WATERMARK_ENABLED
    
    def test_build_flags_none(self):
        """Test no flags."""
        flags = build_flags(
            device_binding=False,
            offline_allowed=False,
            print_allowed=False,
            copy_allowed=False,
            watermark_enabled=False
        )
        
        assert flags == 0


class TestSPDFCreation:
    """Tests for SPDF file creation."""
    
    def test_create_spdf_basic(self, sample_pdf_bytes):
        """Test basic SPDF creation."""
        spdf_bytes, wrapped_key = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TEST-001",
            org_id="test_org",
            server_url="http://localhost:8000",
            title="Test Document"
        )
        
        # Check SPDF starts with magic bytes
        assert spdf_bytes[:4] == b"SPDF"
        
        # Check version
        assert spdf_bytes[4] == 0x01
        
        # Check wrapped key length
        assert len(wrapped_key) == 40
    
    def test_create_spdf_with_permissions(self, sample_pdf_bytes):
        """Test SPDF creation with custom permissions."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TEST-002",
            org_id="test_org",
            server_url="http://localhost:8000",
            allow_print=True,
            allow_copy=True,
            max_devices=5
        )
        
        # Verify SPDF was created
        assert spdf_bytes[:4] == b"SPDF"
    
    def test_create_spdf_unique_keys(self, sample_pdf_bytes):
        """Test that each SPDF gets unique keys."""
        _, key1 = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TEST-003",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        _, key2 = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TEST-004",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        assert key1 != key2


class TestSanitization:
    """Tests for PDF sanitization."""
    
    def test_sanitize_basic_pdf(self, sample_pdf_bytes):
        """Test sanitization of basic PDF."""
        # Should not raise an error
        sanitized = sanitize_pdf(sample_pdf_bytes)
        
        # Should still be valid PDF
        assert sanitized[:4] == b"%PDF"
    
    def test_sanitize_preserves_content(self, sample_pdf_bytes):
        """Test that sanitization preserves basic content."""
        sanitized = sanitize_pdf(sample_pdf_bytes)
        
        # Output should still be non-empty
        assert len(sanitized) > 0
