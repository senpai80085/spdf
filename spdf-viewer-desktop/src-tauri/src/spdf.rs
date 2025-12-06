// SPDF Module - File parsing, signature verification, and decryption

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use base64::{engine::general_purpose, Engine as _};
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;

// Constants
const MAGIC: &[u8] = b"SPDF";
const VERSION: u8 = 1;
const SIGNATURE_LENGTH: usize = 64;
const NONCE_LENGTH: usize = 12;

#[derive(Debug)]
pub enum SpdfError {
    IoError(std::io::Error),
    FormatError(String),
    SignatureError(String),
    DecryptionError(String),
}

impl From<std::io::Error> for SpdfError {
    fn from(err: std::io::Error) -> Self {
        SpdfError::IoError(err)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfPermissions {
    pub allow_print: bool,
    pub allow_copy: bool,
    pub max_devices: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfWatermark {
    pub enabled: bool,
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpdfHeader {
    pub spdf_version: String,
    pub doc_id: String,
    pub org_id: String,
    pub server_url: String,
    pub created_at: String,
    pub permissions: SpdfPermissions,
    pub watermark: SpdfWatermark,
}

pub struct SpdfFile {
    pub header: SpdfHeader,
    pub content: Vec<u8>,
    pub signature: Vec<u8>,
}

impl SpdfFile {
    /// Read and parse SPDF file from path
    pub fn read(path: &str) -> Result<Self, SpdfError> {
        let data = fs::read(path)?;

        // Check minimum size
        if data.len() < 9 {
            return Err(SpdfError::FormatError("File too short".to_string()));
        }

        // Parse MAGIC
        if &data[0..4] != MAGIC {
            return Err(SpdfError::FormatError(format!(
                "Invalid magic bytes. Expected {:?}, got {:?}",
                MAGIC,
                &data[0..4]
            )));
        }

        // Parse VERSION
        let version = data[4];
        if version != VERSION {
            return Err(SpdfError::FormatError(format!(
                "Unsupported version {}",
                version
            )));
        }

        // Parse HEADER_LEN
        let header_len = u32::from_be_bytes([data[5], data[6], data[7], data[8]]) as usize;

        // Parse HEADER_JSON
        let header_start = 9;
        let header_end = header_start + header_len;

        if data.len() < header_end {
            return Err(SpdfError::FormatError("File too short for header".to_string()));
        }

        let header_json = &data[header_start..header_end];
        let header: SpdfHeader = serde_json::from_slice(header_json)
            .map_err(|e| SpdfError::FormatError(format!("Invalid header JSON: {}", e)))?;

        // Extract SIGNATURE (last 64 bytes)
        if data.len() < header_end + SIGNATURE_LENGTH {
            return Err(SpdfError::FormatError(
                "File too short for signature".to_string(),
            ));
        }

        let signature = data[data.len() - SIGNATURE_LENGTH..].to_vec();
        let content = data[header_end..data.len() - SIGNATURE_LENGTH].to_vec();

        Ok(SpdfFile {
            header,
            content,
            signature,
        })
    }

    /// Verify signature using public key (PEM format)
    pub fn verify_signature(&self, public_key_pem: &str) -> Result<(), SpdfError> {
        // Parse PEM to get raw public key bytes
        let public_key_bytes = Self::parse_ed25519_public_key_pem(public_key_pem)?;

        // Create verifying key
        let verifying_key = VerifyingKey::from_bytes(&public_key_bytes)
            .map_err(|e| SpdfError::SignatureError(format!("Invalid public key: {}", e)))?;

        // Reconstruct unsigned data
        let unsigned_data = self.build_unsigned_data()?;

        // Hash the unsigned data
        let mut hasher = Sha256::new();
        hasher.update(&unsigned_data);
        let hash = hasher.finalize();

        // Verify signature
        let signature = Signature::from_bytes(
            &self.signature[0..64]
                .try_into()
                .map_err(|_| SpdfError::SignatureError("Invalid signature length".to_string()))?,
        );

        verifying_key
            .verify(&hash, &signature)
            .map_err(|e| SpdfError::SignatureError(format!("Signature verification failed: {}", e)))?;

        Ok(())
    }

    /// Decrypt content using k_doc
    pub fn decrypt(&self, k_doc: &[u8; 32]) -> Result<Vec<u8>, SpdfError> {
        if self.content.len() < NONCE_LENGTH + 16 {
            return Err(SpdfError::DecryptionError(
                "Content too short for nonce and tag".to_string(),
            ));
        }

        // Extract nonce (first 12 bytes)
        let nonce_bytes: [u8; 12] = self.content[0..NONCE_LENGTH]
            .try_into()
            .map_err(|_| SpdfError::DecryptionError("Invalid nonce length".to_string()))?;
        let nonce = Nonce::from_slice(&nonce_bytes);

        // Extract ciphertext + tag (rest of content)
        let ciphertext_with_tag = &self.content[NONCE_LENGTH..];

        // Decrypt
        let cipher = Aes256Gcm::new(k_doc.into());
        let plaintext = cipher
            .decrypt(nonce, ciphertext_with_tag)
            .map_err(|e| SpdfError::DecryptionError(format!("Decryption failed: {}", e)))?;

        Ok(plaintext)
    }

    /// Build unsigned data for signature verification
    fn build_unsigned_data(&self) -> Result<Vec<u8>, SpdfError> {
        let mut data = Vec::new();

        // MAGIC
        data.extend_from_slice(MAGIC);

        // VERSION
        data.push(VERSION);

        // HEADER_JSON
        let header_json = serde_json::to_vec(&self.header)
            .map_err(|e| SpdfError::FormatError(format!("Failed to serialize header: {}", e)))?;
        let header_len = header_json.len() as u32;

        // HEADER_LEN
        data.extend_from_slice(&header_len.to_be_bytes());

        // HEADER_JSON
        data.extend_from_slice(&header_json);

        // CONTENT
        data.extend_from_slice(&self.content);

        Ok(data)
    }

    /// Parse Ed25519 public key from PEM format
    fn parse_ed25519_public_key_pem(pem: &str) -> Result<[u8; 32], SpdfError> {
        // Simple PEM parser for Ed25519 public keys
        let pem = pem.replace("-----BEGIN PUBLIC KEY-----", "");
        let pem = pem.replace("-----END PUBLIC KEY-----", "");
        let pem = pem.replace("\n", "").replace("\r", "");

        let decoded = general_purpose::STANDARD.decode(&pem)
            .map_err(|e| SpdfError::FormatError(format!("Invalid PEM base64: {}", e)))?;

        // Ed25519 public key in SubjectPublicKeyInfo format is 44 bytes,
        // last 32 bytes are the actual key
        if decoded.len() < 32 {
            return Err(SpdfError::FormatError(
                "PEM decoded data too short".to_string(),
            ));
        }

        let key_bytes: [u8; 32] = decoded[decoded.len() - 32..]
            .try_into()
            .map_err(|_| SpdfError::FormatError("Invalid key length".to_string()))?;

        Ok(key_bytes)
    }
}
