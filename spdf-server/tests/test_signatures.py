"""
Signature Module Tests

Tests for Ed25519 signature functionality.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.signature import (
    sign_data,
    verify_signature,
    verify_signature_pem,
    SignatureError,
    load_private_key_pem,
    load_public_key_pem,
    export_public_key_pem
)
from crypto.keys import KeyManager


class TestSignature:
    """Tests for signature functions."""
    
    def test_sign_and_verify(self, key_manager):
        """Test basic sign and verify flow."""
        data = b"Test data to sign"
        
        private_key = key_manager.get_signing_key()
        public_key = key_manager.get_public_key()
        
        # Sign
        signature = sign_data(data, private_key)
        
        # Verify
        assert len(signature) == 64
        result = verify_signature(data, signature, public_key)
        assert result is True
    
    def test_verify_with_wrong_data(self, key_manager):
        """Test that modified data fails verification."""
        data = b"Original data"
        modified_data = b"Modified data"
        
        private_key = key_manager.get_signing_key()
        public_key = key_manager.get_public_key()
        
        signature = sign_data(data, private_key)
        
        # Verification of modified data should fail
        with pytest.raises(SignatureError):
            verify_signature(modified_data, signature, public_key)
    
    def test_verify_with_wrong_signature(self, key_manager):
        """Test that wrong signature fails verification."""
        data = b"Test data"
        
        public_key = key_manager.get_public_key()
        
        # Random fake signature
        fake_signature = b"\x00" * 64
        
        with pytest.raises(SignatureError):
            verify_signature(data, fake_signature, public_key)
    
    def test_verify_with_invalid_signature_length(self, key_manager):
        """Test that invalid signature length is rejected."""
        data = b"Test data"
        public_key = key_manager.get_public_key()
        
        short_signature = b"\x00" * 32
        
        with pytest.raises(SignatureError):
            verify_signature(data, short_signature, public_key)
    
    def test_verify_with_pem(self, key_manager):
        """Test verification using PEM-encoded key."""
        data = b"Test data for PEM verification"
        
        private_key = key_manager.get_signing_key()
        public_key_pem = key_manager.get_public_key_pem()
        
        signature = sign_data(data, private_key)
        
        result = verify_signature_pem(data, signature, public_key_pem)
        assert result is True
    
    def test_sign_empty_data(self, key_manager):
        """Test signing empty data."""
        data = b""
        
        private_key = key_manager.get_signing_key()
        public_key = key_manager.get_public_key()
        
        signature = sign_data(data, private_key)
        
        assert len(signature) == 64
        result = verify_signature(data, signature, public_key)
        assert result is True
    
    def test_sign_large_data(self, key_manager):
        """Test signing large data."""
        data = b"x" * 10_000_000  # 10MB
        
        private_key = key_manager.get_signing_key()
        public_key = key_manager.get_public_key()
        
        signature = sign_data(data, private_key)
        
        assert len(signature) == 64
        result = verify_signature(data, signature, public_key)
        assert result is True


class TestKeySerialization:
    """Tests for key PEM serialization."""
    
    def test_export_public_key_pem(self, key_manager):
        """Test exporting public key to PEM."""
        public_key = key_manager.get_public_key()
        pem = export_public_key_pem(public_key)
        
        assert "-----BEGIN PUBLIC KEY-----" in pem
        assert "-----END PUBLIC KEY-----" in pem
    
    def test_round_trip_public_key(self, key_manager):
        """Test public key can be exported and imported."""
        public_key = key_manager.get_public_key()
        pem = export_public_key_pem(public_key)
        
        loaded_key = load_public_key_pem(pem)
        
        # Verify they work the same
        data = b"Test"
        private_key = key_manager.get_signing_key()
        signature = sign_data(data, private_key)
        
        # Both should verify successfully
        assert verify_signature(data, signature, public_key)
        assert verify_signature(data, signature, loaded_key)
