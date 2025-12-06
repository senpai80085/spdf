"""
Test Configuration and Fixtures

This module provides shared fixtures for all tests.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Set up test environment
os.environ.setdefault("SPDF_MASTER_KEY", "0" * 64)  # Test key

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf_bytes():
    """Create minimal valid PDF bytes for testing."""
    # Minimal valid PDF structure
    pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
196
%%EOF
"""
    return pdf


@pytest.fixture
def sample_pdf_file(temp_dir, sample_pdf_bytes):
    """Create a sample PDF file."""
    pdf_path = temp_dir / "test.pdf"
    pdf_path.write_bytes(sample_pdf_bytes)
    return pdf_path


@pytest.fixture
def key_manager():
    """Create a KeyManager instance for testing."""
    from crypto.keys import KeyManager
    return KeyManager("test_org")


@pytest.fixture
def master_key():
    """Generate a test master key."""
    from crypto.keys import KeyManager
    return KeyManager.generate_master_key()


@pytest.fixture
def doc_key():
    """Generate a test document key."""
    from crypto.keys import KeyManager
    return KeyManager.generate_doc_key()
