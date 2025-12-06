"""
SPDF Format Tests

Tests for SPDF file format parsing and validation.
"""

import pytest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto.decrypt import (
    parse_spdf,
    parse_spdf_file,
    verify_signature,
    get_spdf_info,
    FormatError,
    SignatureError
)
from crypto.encrypt import create_spdf
from crypto.format import (
    MAGIC,
    VERSION,
    validate_magic,
    get_version,
    parse_flags
)


class TestMagicBytes:
    """Tests for SPDF magic bytes."""
    
    def test_validate_magic_valid(self):
        """Test valid magic bytes."""
        assert validate_magic(b"SPDF")
        assert validate_magic(b"SPDFextradata")
    
    def test_validate_magic_invalid(self):
        """Test invalid magic bytes."""
        assert not validate_magic(b"PDF")
        assert not validate_magic(b"SP")
        assert not validate_magic(b"")
        assert not validate_magic(b"XPDF")
    
    def test_magic_constant(self):
        """Test magic constant value."""
        assert MAGIC == b"SPDF"


class TestVersionParsing:
    """Tests for version parsing."""
    
    def test_version_constant(self):
        """Test version constant."""
        assert VERSION == 0x01
    
    def test_get_version(self):
        """Test extracting version from data."""
        data = b"SPDF\x01\x00\x00extra"
        version = get_version(data)
        assert version == 1
    
    def test_get_version_too_short(self):
        """Test error on short data."""
        with pytest.raises(ValueError):
            get_version(b"SPDF")


class TestFlagParsing:
    """Tests for flag parsing."""
    
    def test_parse_flags_none(self):
        """Test parsing no flags."""
        result = parse_flags(0x0000)
        
        assert result["device_binding"] is False
        assert result["offline_allowed"] is False
        assert result["print_allowed"] is False
        assert result["copy_allowed"] is False
    
    def test_parse_flags_all(self):
        """Test parsing all flags."""
        result = parse_flags(0x001F)
        
        assert result["device_binding"] is True
        assert result["offline_allowed"] is True
        assert result["print_allowed"] is True
        assert result["copy_allowed"] is True
        assert result["watermark_enabled"] is True
    
    def test_parse_flags_individual(self):
        """Test parsing individual flags."""
        # Device binding only
        result = parse_flags(0x0001)
        assert result["device_binding"] is True
        assert result["print_allowed"] is False
        
        # Print only
        result = parse_flags(0x0004)
        assert result["print_allowed"] is True
        assert result["device_binding"] is False


class TestSPDFParsing:
    """Tests for SPDF file parsing."""
    
    def test_parse_complete_spdf(self, sample_pdf_bytes):
        """Test parsing a complete SPDF file."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="PARSE-TEST-001",
            org_id="test_org",
            server_url="http://localhost:8000",
            title="Test Document"
        )
        
        # Parse
        spdf = parse_spdf(spdf_bytes)
        
        assert spdf.version == 1
        assert spdf.header.doc_id == "PARSE-TEST-001"
        assert spdf.header.org_id == "test_org"
        assert spdf.header.title == "Test Document"
        assert len(spdf.wrapped_key) == 40
        assert len(spdf.nonce) == 12
        assert len(spdf.auth_tag) == 16
        assert len(spdf.signature) == 64
    
    def test_parse_invalid_magic(self):
        """Test error on invalid magic bytes."""
        data = b"XPDF\x01\x00\x00rest of data..."
        
        with pytest.raises(FormatError):
            parse_spdf(data)
    
    def test_parse_invalid_version(self):
        """Test error on unsupported version."""
        data = b"SPDF\x99\x00\x00rest..."
        
        with pytest.raises(FormatError):
            parse_spdf(data)
    
    def test_parse_too_short(self):
        """Test error on too-short data."""
        with pytest.raises(FormatError):
            parse_spdf(b"SPDF")
    
    def test_get_spdf_info(self, sample_pdf_bytes):
        """Test getting info without full decryption."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="INFO-TEST",
            org_id="info_org",
            server_url="http://test.com",
            allow_print=True,
            max_devices=5
        )
        
        info = get_spdf_info(spdf_bytes)
        
        assert info["doc_id"] == "INFO-TEST"
        assert info["org_id"] == "info_org"
        assert info["permissions"]["allow_print"] is True
        assert info["permissions"]["max_devices"] == 5


class TestTamperDetection:
    """Tests for tamper detection."""
    
    def test_detect_modified_ciphertext(self, sample_pdf_bytes):
        """Test that modified ciphertext is detected."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TAMPER-001",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        # Modify the ciphertext (somewhere in the middle)
        modified = bytearray(spdf_bytes)
        modified[len(modified) // 2] ^= 0xFF
        
        # Parse and verify - should fail
        spdf = parse_spdf(bytes(modified))
        
        with pytest.raises(SignatureError):
            verify_signature(spdf)
    
    def test_detect_modified_header(self, sample_pdf_bytes):
        """Test that modified header is detected."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TAMPER-002",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        # Modify header area
        modified = bytearray(spdf_bytes)
        modified[20] ^= 0xFF  # Somewhere in header
        
        try:
            spdf = parse_spdf(bytes(modified))
            # If parsing succeeds, signature should fail
            with pytest.raises(SignatureError):
                verify_signature(spdf)
        except FormatError:
            # Also acceptable - corrupted header isn't valid JSON
            pass
    
    def test_detect_modified_signature(self, sample_pdf_bytes):
        """Test that modified signature fails verification."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="TAMPER-003",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        # Modify the signature (last 64 bytes)
        modified = bytearray(spdf_bytes)
        modified[-10] ^= 0xFF
        
        spdf = parse_spdf(bytes(modified))
        
        with pytest.raises(SignatureError):
            verify_signature(spdf)
    
    def test_valid_signature_passes(self, sample_pdf_bytes):
        """Test that valid file passes verification."""
        spdf_bytes, _ = create_spdf(
            pdf_bytes=sample_pdf_bytes,
            doc_id="VALID-001",
            org_id="test_org",
            server_url="http://localhost:8000"
        )
        
        spdf = parse_spdf(spdf_bytes)
        
        # Should not raise
        verify_signature(spdf)
