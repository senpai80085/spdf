"""
License Module Tests

Tests for license validation and enforcement.
"""

import pytest
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.license import (
    generate_license_key,
    check_rate_limit,
    check_brute_force,
    record_failed_attempt,
    clear_failed_attempts,
    _rate_limit_store,
    _failed_attempts
)


class TestLicenseKeyGeneration:
    """Tests for license key generation."""
    
    def test_generate_license_key_format(self):
        """Test license key format."""
        key = generate_license_key()
        
        # Format: SPDF-XXXX-XXXX-XXXX-XXXX
        assert key.startswith("SPDF-")
        parts = key.split("-")
        assert len(parts) == 5
        assert all(len(p) == 4 for p in parts[1:])
    
    def test_generate_license_key_uniqueness(self):
        """Test that each key is unique."""
        keys = [generate_license_key() for _ in range(100)]
        assert len(set(keys)) == 100
    
    def test_generate_license_key_characters(self):
        """Test that key uses valid characters."""
        key = generate_license_key()
        
        # Remove prefix and dashes
        chars = key.replace("SPDF-", "").replace("-", "")
        
        # Should only contain uppercase letters and digits
        assert all(c.isupper() or c.isdigit() for c in chars)


class TestRateLimiting:
    """Tests for rate limiting."""
    
    def setup_method(self):
        """Clear rate limit store before each test."""
        _rate_limit_store.clear()
    
    def test_rate_limit_allows_initial_requests(self):
        """Test that initial requests are allowed."""
        assert check_rate_limit("192.168.1.1") is True
        assert check_rate_limit("192.168.1.1") is True
    
    def test_rate_limit_blocks_excessive_requests(self):
        """Test that excessive requests are blocked."""
        ip = "192.168.1.2"
        
        # Make many requests quickly
        for _ in range(25):
            check_rate_limit(ip)
        
        # Should eventually be blocked
        results = [check_rate_limit(ip) for _ in range(10)]
        assert False in results
    
    def test_rate_limit_different_ips(self):
        """Test that rate limits are per-IP."""
        # Fill up rate limit for one IP
        ip1 = "192.168.1.3"
        for _ in range(30):
            check_rate_limit(ip1)
        
        # Different IP should still work
        ip2 = "192.168.1.4"
        assert check_rate_limit(ip2) is True


class TestBruteForceProtection:
    """Tests for brute force protection."""
    
    def setup_method(self):
        """Clear failed attempts before each test."""
        _failed_attempts.clear()
    
    def test_brute_force_allows_initial_failures(self):
        """Test that initial failures don't trigger lockout."""
        ip = "10.0.0.1"
        key = "SPDF-TEST-1234-5678-ABCD"
        
        assert check_brute_force(ip, key) is False
        record_failed_attempt(ip, key)
        assert check_brute_force(ip, key) is False
    
    def test_brute_force_triggers_lockout(self):
        """Test that repeated failures trigger lockout."""
        ip = "10.0.0.2"
        key = "SPDF-TEST-2222-3333-4444"
        
        # Record multiple failures
        for _ in range(6):
            record_failed_attempt(ip, key)
        
        # Should now be blocked
        assert check_brute_force(ip, key) is True
    
    def test_brute_force_clears_on_success(self):
        """Test that successful auth clears failures."""
        ip = "10.0.0.3"
        key = "SPDF-TEST-3333-4444-5555"
        
        # Record some failures
        for _ in range(3):
            record_failed_attempt(ip, key)
        
        # Clear on success
        clear_failed_attempts(ip, key)
        
        # More failures should be allowed
        for _ in range(3):
            record_failed_attempt(ip, key)
        
        # Not blocked yet (less than threshold)
        assert check_brute_force(ip, key) is False
    
    def test_brute_force_different_keys(self):
        """Test that brute force tracking is per-key."""
        ip = "10.0.0.4"
        key1 = "SPDF-KEY1-1111-1111-1111"
        key2 = "SPDF-KEY2-2222-2222-2222"
        
        # Trigger lockout for key1
        for _ in range(6):
            record_failed_attempt(ip, key1)
        
        # key2 should not be affected
        assert check_brute_force(ip, key2) is False


class TestLicenseValidation:
    """Tests for license validation logic."""
    
    def test_license_key_regex_pattern(self):
        """Test license key format validation."""
        import re
        pattern = r'^SPDF-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
        
        # Valid keys
        assert re.match(pattern, "SPDF-ABCD-1234-EFGH-5678")
        assert re.match(pattern, "SPDF-0000-0000-0000-0000")
        assert re.match(pattern, "SPDF-ZZZZ-9999-AAAA-0000")
        
        # Invalid keys
        assert not re.match(pattern, "spdf-abcd-1234-efgh-5678")  # lowercase
        assert not re.match(pattern, "SPDF-ABC-1234-EFGH-5678")   # short segment
        assert not re.match(pattern, "PDF-ABCD-1234-EFGH-5678")   # wrong prefix
        assert not re.match(pattern, "SPDF-ABCD-1234-EFGH")       # missing segment
