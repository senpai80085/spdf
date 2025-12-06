"""
SPDF Format Module

Provides SPDF file format utilities and constants.
"""

import struct
from typing import Dict, Any
from dataclasses import dataclass, asdict

# Magic bytes
MAGIC = b"SPDF"
MAGIC_STR = "SPDF"

# Version
VERSION = 0x01

# Lengths
NONCE_LENGTH = 12
TAG_LENGTH = 16
SIGNATURE_LENGTH = 64
WRAPPED_KEY_LENGTH = 40

# Flag bits
FLAG_DEVICE_BINDING = 0x0001
FLAG_OFFLINE_ALLOWED = 0x0002
FLAG_PRINT_ALLOWED = 0x0004
FLAG_COPY_ALLOWED = 0x0008
FLAG_WATERMARK_ENABLED = 0x0010

# Minimum file size: MAGIC(4) + VERSION(1) + FLAGS(2) + HEADER_LEN(4) + 
#                    min_header + WRAPPED_KEY(40) + NONCE(12) + TAG(16) + SIGNATURE(64)
MIN_FILE_SIZE = 4 + 1 + 2 + 4 + 2 + 40 + 12 + 16 + 64  # 145 bytes minimum


@dataclass
class Permissions:
    """Document permissions."""
    allow_print: bool = False
    allow_copy: bool = False
    max_devices: int = 2
    offline_days: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Watermark:
    """Watermark configuration."""
    enabled: bool = True
    text: str = "{{user_email}} | {{device_id}}"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_flags(permissions: Permissions, device_binding: bool = True) -> int:
    """Build flags integer from permissions."""
    flags = 0
    if device_binding:
        flags |= FLAG_DEVICE_BINDING
    if permissions.offline_days > 0:
        flags |= FLAG_OFFLINE_ALLOWED
    if permissions.allow_print:
        flags |= FLAG_PRINT_ALLOWED
    if permissions.allow_copy:
        flags |= FLAG_COPY_ALLOWED
    return flags


def parse_flags(flags: int) -> Dict[str, bool]:
    """Parse flags integer to dictionary."""
    return {
        "device_binding": bool(flags & FLAG_DEVICE_BINDING),
        "offline_allowed": bool(flags & FLAG_OFFLINE_ALLOWED),
        "print_allowed": bool(flags & FLAG_PRINT_ALLOWED),
        "copy_allowed": bool(flags & FLAG_COPY_ALLOWED),
        "watermark_enabled": bool(flags & FLAG_WATERMARK_ENABLED)
    }


def validate_magic(data: bytes) -> bool:
    """Check if data starts with SPDF magic bytes."""
    return len(data) >= 4 and data[:4] == MAGIC


def get_header_length(data: bytes) -> int:
    """Get header length from SPDF data."""
    if len(data) < 11:
        raise ValueError("Data too short")
    return struct.unpack('>I', data[7:11])[0]


def get_version(data: bytes) -> int:
    """Get version from SPDF data."""
    if len(data) < 5:
        raise ValueError("Data too short")
    return data[4]
