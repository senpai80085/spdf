"""
Key Management Tests

Tests for key generation, wrapping, and rotation.
"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.keys import (
    KeyManager,
    KeyManagementError,
    MASTER_KEY_LENGTH,
    DOC_KEY_LENGTH,
    WRAPPED_KEY_LENGTH,
    hash_device_info,
    generate_device_salt
)


class TestKeyGeneration:
    """Tests for key generation."""
    
    def test_generate_master_key(self):
        """Test master key generation."""
        key = KeyManager.generate_master_key()
        
        assert len(key) == MASTER_KEY_LENGTH
        assert isinstance(key, bytes)
    
    def test_generate_master_key_uniqueness(self):
        """Test that each call generates unique key."""
        key1 = KeyManager.generate_master_key()
        key2 = KeyManager.generate_master_key()
        
        assert key1 != key2
    
    def test_generate_doc_key(self):
        """Test document key generation."""
        key = KeyManager.generate_doc_key()
        
        assert len(key) == DOC_KEY_LENGTH
        assert isinstance(key, bytes)
    
    def test_generate_doc_key_uniqueness(self):
        """Test that each call generates unique key."""
        key1 = KeyManager.generate_doc_key()
        key2 = KeyManager.generate_doc_key()
        
        assert key1 != key2


class TestKeyWrapping:
    """Tests for key wrapping and unwrapping."""
    
    def test_wrap_key(self, key_manager, doc_key):
        """Test key wrapping."""
        wrapped = key_manager.wrap_key(doc_key)
        
        assert len(wrapped) == WRAPPED_KEY_LENGTH
        assert wrapped != doc_key
    
    def test_wrap_unwrap_round_trip(self, key_manager, doc_key):
        """Test wrapping and unwrapping returns original key."""
        wrapped = key_manager.wrap_key(doc_key)
        unwrapped = key_manager.unwrap_key(wrapped)
        
        assert unwrapped == doc_key
    
    def test_wrap_invalid_key_length(self, key_manager):
        """Test wrapping rejects invalid key length."""
        short_key = b"short"
        
        with pytest.raises(KeyManagementError):
            key_manager.wrap_key(short_key)
    
    def test_unwrap_invalid_wrapped_key_length(self, key_manager):
        """Test unwrapping rejects invalid wrapped key length."""
        invalid_wrapped = b"x" * 20
        
        with pytest.raises(KeyManagementError):
            key_manager.unwrap_key(invalid_wrapped)
    
    def test_unwrap_corrupted_key(self, key_manager, doc_key):
        """Test unwrapping fails on corrupted data."""
        wrapped = key_manager.wrap_key(doc_key)
        
        # Corrupt the wrapped key
        corrupted = bytearray(wrapped)
        corrupted[10] ^= 0xFF
        
        with pytest.raises(KeyManagementError):
            key_manager.unwrap_key(bytes(corrupted))


class TestKeyRotation:
    """Tests for master key rotation."""
    
    def test_rotate_master_key(self, key_manager):
        """Test master key rotation."""
        # Create some wrapped keys
        doc_keys = [KeyManager.generate_doc_key() for _ in range(5)]
        wrapped_keys = [key_manager.wrap_key(k) for k in doc_keys]
        
        # Generate new master key
        new_master = KeyManager.generate_master_key()
        
        # Rotate
        new_wrapped = key_manager.rotate_master_key(new_master, wrapped_keys)
        
        # Verify new wrapped keys work
        assert len(new_wrapped) == len(wrapped_keys)
        
        for i, new_wrap in enumerate(new_wrapped):
            unwrapped = key_manager.unwrap_key(new_wrap)
            assert unwrapped == doc_keys[i]
    
    def test_rotate_empty_list(self, key_manager):
        """Test rotation with empty key list."""
        new_master = KeyManager.generate_master_key()
        new_wrapped = key_manager.rotate_master_key(new_master, [])
        
        assert new_wrapped == []
    
    def test_rotate_invalid_new_master(self, key_manager, doc_key):
        """Test rotation with invalid new master key."""
        wrapped = key_manager.wrap_key(doc_key)
        
        short_master = b"short"
        
        with pytest.raises(KeyManagementError):
            key_manager.rotate_master_key(short_master, [wrapped])


class TestSigningKeys:
    """Tests for Ed25519 signing keys."""
    
    def test_get_signing_key(self, key_manager):
        """Test getting signing key."""
        key = key_manager.get_signing_key()
        
        # Should be an Ed25519 private key
        assert key is not None
    
    def test_get_signing_key_consistent(self, key_manager):
        """Test that same key is returned on subsequent calls."""
        key1 = key_manager.get_signing_key()
        key2 = key_manager.get_signing_key()
        
        # Should be the same object
        assert key1 is key2
    
    def test_get_public_key(self, key_manager):
        """Test getting public key."""
        public_key = key_manager.get_public_key()
        
        assert public_key is not None
    
    def test_get_public_key_pem(self, key_manager):
        """Test getting public key as PEM."""
        pem = key_manager.get_public_key_pem()
        
        assert "-----BEGIN PUBLIC KEY-----" in pem
        assert "-----END PUBLIC KEY-----" in pem
    
    def test_different_orgs_different_keys(self):
        """Test that different orgs get different keys."""
        km1 = KeyManager("org1")
        km2 = KeyManager("org2")
        
        pem1 = km1.get_public_key_pem()
        pem2 = km2.get_public_key_pem()
        
        # Different orgs should have different keys
        assert pem1 != pem2


class TestDeviceHashing:
    """Tests for device fingerprint hashing."""
    
    def test_generate_device_salt(self):
        """Test salt generation."""
        salt = generate_device_salt()
        
        assert len(salt) == 16
        assert isinstance(salt, bytes)
    
    def test_hash_device_info(self):
        """Test device info hashing."""
        salt = generate_device_salt()
        
        device_hash = hash_device_info(
            cpu_id="Intel Core i7",
            mac_address="00:11:22:33:44:55",
            os_info="Windows 11",
            salt=salt
        )
        
        # Should be hex SHA-256
        assert len(device_hash) == 64
        assert all(c in "0123456789abcdef" for c in device_hash)
    
    def test_hash_device_info_deterministic(self):
        """Test that same inputs produce same hash."""
        salt = b"fixed_salt_16b!!"
        
        hash1 = hash_device_info("cpu", "00:11:22:33:44:55", "os", salt)
        hash2 = hash_device_info("cpu", "00:11:22:33:44:55", "os", salt)
        
        assert hash1 == hash2
    
    def test_hash_device_info_different_salt(self):
        """Test that different salt produces different hash."""
        salt1 = b"salt_one_16bytes"
        salt2 = b"salt_two_16bytes"
        
        hash1 = hash_device_info("cpu", "00:11:22:33:44:55", "os", salt1)
        hash2 = hash_device_info("cpu", "00:11:22:33:44:55", "os", salt2)
        
        assert hash1 != hash2
