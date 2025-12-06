// SPDF Parser Module - File parsing and validation
//
// This module provides functionality for parsing SPDF files according
// to the v1.0 specification.

use serde::{Deserialize, Serialize};
use std::fs;

// Constants matching the SPDF specification
pub const MAGIC: &[u8] = b"SPDF";
pub const VERSION: u8 = 0x01;
pub const SIGNATURE_LENGTH: usize = 64;
pub const NONCE_LENGTH: usize = 12;
pub const TAG_LENGTH: usize = 16;
pub const WRAPPED_KEY_LENGTH: usize = 40;

// Flag bits
pub const FLAG_DEVICE_BINDING: u16 = 0x0001;
pub const FLAG_OFFLINE_ALLOWED: u16 = 0x0002;
pub const FLAG_PRINT_ALLOWED: u16 = 0x0004;
pub const FLAG_COPY_ALLOWED: u16 = 0x0008;
pub const FLAG_WATERMARK_ENABLED: u16 = 0x0010;

/// Errors that can occur during SPDF parsing
#[derive(Debug)]
pub enum SpdfError {
    IoError(std::io::Error),
    FormatError(String),
    SignatureError(String),
    DecryptionError(String),
    NetworkError(String),
    LicenseError(String),
}

impl std::fmt::Display for SpdfError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpdfError::IoError(e) => write!(f, "IO error: {}", e),
            SpdfError::FormatError(msg) => write!(f, "Format error: {}", msg),
            SpdfError::SignatureError(msg) => write!(f, "Signature error: {}", msg),
            SpdfError::DecryptionError(msg) => write!(f, "Decryption error: {}", msg),
            SpdfError::NetworkError(msg) => write!(f, "Network error: {}", msg),
            SpdfError::LicenseError(msg) => write!(f, "License error: {}", msg),
        }
    }
}

impl std::error::Error for SpdfError {}

impl From<std::io::Error> for SpdfError {
    fn from(err: std::io::Error) -> Self {
        SpdfError::IoError(err)
    }
}

impl From<serde_json::Error> for SpdfError {
    fn from(err: serde_json::Error) -> Self {
        SpdfError::FormatError(format!("JSON parse error: {}", err))
    }
}

/// SPDF file permissions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfPermissions {
    pub allow_print: bool,
    pub allow_copy: bool,
    pub max_devices: u32,
    #[serde(default)]
    pub offline_days: u32,
}

impl Default for SpdfPermissions {
    fn default() -> Self {
        SpdfPermissions {
            allow_print: false,
            allow_copy: false,
            max_devices: 2,
            offline_days: 0,
        }
    }
}

/// SPDF watermark configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfWatermark {
    pub enabled: bool,
    pub text: String,
}

impl Default for SpdfWatermark {
    fn default() -> Self {
        SpdfWatermark {
            enabled: true,
            text: "{{user_email}} | {{device_id}}".to_string(),
        }
    }
}

/// SPDF file header
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfHeader {
    pub spdf_version: String,
    pub doc_id: String,
    pub org_id: String,
    #[serde(default)]
    pub title: String,
    pub server_url: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub public_key: String,
    #[serde(default)]
    pub permissions: SpdfPermissions,
    #[serde(default)]
    pub watermark: SpdfWatermark,
    #[serde(default)]
    pub metadata: serde_json::Value,
}

/// Parsed SPDF file structure
pub struct SpdfFile {
    pub version: u8,
    pub flags: u16,
    pub header: SpdfHeader,
    pub wrapped_key: Vec<u8>,
    pub nonce: Vec<u8>,
    pub ciphertext: Vec<u8>,
    pub auth_tag: Vec<u8>,
    pub signature: Vec<u8>,
    pub unsigned_data: Vec<u8>,
}

impl SpdfFile {
    /// Read and parse an SPDF file from disk
    pub fn read(path: &str) -> Result<Self, SpdfError> {
        let data = fs::read(path)?;
        Self::parse(&data)
    }

    /// Parse SPDF data from bytes
    pub fn parse(data: &[u8]) -> Result<Self, SpdfError> {
        let mut pos = 0;

        // Minimum size check
        let min_size = 4 + 1 + 2 + 4 + WRAPPED_KEY_LENGTH + NONCE_LENGTH + TAG_LENGTH + SIGNATURE_LENGTH;
        if data.len() < min_size {
            return Err(SpdfError::FormatError(format!(
                "File too short: {} bytes, minimum {} bytes",
                data.len(),
                min_size
            )));
        }

        // Parse MAGIC (4 bytes)
        if &data[pos..pos + 4] != MAGIC {
            return Err(SpdfError::FormatError(format!(
                "Invalid magic bytes: expected {:?}, got {:?}",
                MAGIC,
                &data[pos..pos + 4]
            )));
        }
        pos += 4;

        // Parse VERSION (1 byte)
        let version = data[pos];
        if version != VERSION {
            return Err(SpdfError::FormatError(format!(
                "Unsupported version: {}, expected {}",
                version, VERSION
            )));
        }
        pos += 1;

        // Parse FLAGS (2 bytes, big-endian)
        let flags = u16::from_be_bytes([data[pos], data[pos + 1]]);
        pos += 2;

        // Parse HEADER_LEN (4 bytes, big-endian)
        let header_len = u32::from_be_bytes([data[pos], data[pos + 1], data[pos + 2], data[pos + 3]]) as usize;
        pos += 4;

        // Validate header length
        if pos + header_len > data.len() {
            return Err(SpdfError::FormatError(format!(
                "Invalid header length: {} exceeds file size",
                header_len
            )));
        }

        // Parse HEADER_JSON
        let header_json = &data[pos..pos + header_len];
        let header: SpdfHeader = serde_json::from_slice(header_json)?;
        pos += header_len;

        // Parse WRAPPED_KEY (40 bytes)
        if pos + WRAPPED_KEY_LENGTH > data.len() {
            return Err(SpdfError::FormatError("File too short for wrapped key".to_string()));
        }
        let wrapped_key = data[pos..pos + WRAPPED_KEY_LENGTH].to_vec();
        pos += WRAPPED_KEY_LENGTH;

        // Parse NONCE (12 bytes)
        if pos + NONCE_LENGTH > data.len() {
            return Err(SpdfError::FormatError("File too short for nonce".to_string()));
        }
        let nonce = data[pos..pos + NONCE_LENGTH].to_vec();
        pos += NONCE_LENGTH;

        // Signature is always last 64 bytes
        if data.len() < pos + TAG_LENGTH + SIGNATURE_LENGTH {
            return Err(SpdfError::FormatError("File too short for tag and signature".to_string()));
        }

        let signature = data[data.len() - SIGNATURE_LENGTH..].to_vec();
        let unsigned_data = data[..data.len() - SIGNATURE_LENGTH].to_vec();

        // Ciphertext is between nonce and (auth_tag + signature)
        let ciphertext_end = data.len() - SIGNATURE_LENGTH - TAG_LENGTH;
        if ciphertext_end <= pos {
            return Err(SpdfError::FormatError("Invalid ciphertext length".to_string()));
        }

        let ciphertext = data[pos..ciphertext_end].to_vec();
        let auth_tag = data[ciphertext_end..ciphertext_end + TAG_LENGTH].to_vec();

        Ok(SpdfFile {
            version,
            flags,
            header,
            wrapped_key,
            nonce,
            ciphertext,
            auth_tag,
            signature,
            unsigned_data,
        })
    }

    /// Check if device binding is required
    pub fn requires_device_binding(&self) -> bool {
        self.flags & FLAG_DEVICE_BINDING != 0
    }

    /// Check if offline viewing is allowed
    pub fn allows_offline(&self) -> bool {
        self.flags & FLAG_OFFLINE_ALLOWED != 0
    }

    /// Check if printing is allowed
    pub fn allows_print(&self) -> bool {
        self.flags & FLAG_PRINT_ALLOWED != 0
    }

    /// Check if copying is allowed
    pub fn allows_copy(&self) -> bool {
        self.flags & FLAG_COPY_ALLOWED != 0
    }

    /// Check if watermark is enabled
    pub fn has_watermark(&self) -> bool {
        self.flags & FLAG_WATERMARK_ENABLED != 0
    }

    /// Get document ID
    pub fn doc_id(&self) -> &str {
        &self.header.doc_id
    }

    /// Get server URL
    pub fn server_url(&self) -> &str {
        &self.header.server_url
    }

    /// Get organization ID
    pub fn org_id(&self) -> &str {
        &self.header.org_id
    }

    /// Get title
    pub fn title(&self) -> &str {
        &self.header.title
    }
}

/// Validate SPDF magic bytes without full parsing
pub fn validate_magic(data: &[u8]) -> bool {
    data.len() >= 4 && &data[0..4] == MAGIC
}

/// Get basic info from SPDF without full parsing
pub fn quick_info(data: &[u8]) -> Result<(String, String, String), SpdfError> {
    let spdf = SpdfFile::parse(data)?;
    Ok((
        spdf.header.doc_id,
        spdf.header.title,
        spdf.header.server_url,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_magic() {
        assert!(validate_magic(b"SPDF"));
        assert!(validate_magic(b"SPDFextradata"));
        assert!(!validate_magic(b"PDF"));
        assert!(!validate_magic(b""));
    }

    #[test]
    fn test_parse_invalid_magic() {
        let data = b"INVALID_DATA";
        let result = SpdfFile::parse(data);
        assert!(matches!(result, Err(SpdfError::FormatError(_))));
    }

    #[test]
    fn test_parse_too_short() {
        let data = b"SPDF";
        let result = SpdfFile::parse(data);
        assert!(matches!(result, Err(SpdfError::FormatError(_))));
    }
}
