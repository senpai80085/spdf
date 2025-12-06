// Verify Module - Ed25519 signature verification for SPDF files
//
// This module provides signature verification to ensure SPDF files
// have not been tampered with.

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use sha2::{Sha256, Digest};
use base64::{engine::general_purpose, Engine as _};

use crate::spdf_parser::{SpdfFile, SpdfError, SIGNATURE_LENGTH};

/// Verify the Ed25519 signature of an SPDF file
///
/// # Arguments
/// * `spdf` - Parsed SPDF file
///
/// # Returns
/// Ok(()) if signature is valid, Err otherwise
pub fn verify_signature(spdf: &SpdfFile) -> Result<(), SpdfError> {
    // Get public key from header
    let public_key_pem = &spdf.header.public_key;
    if public_key_pem.is_empty() {
        return Err(SpdfError::SignatureError("No public key in header".to_string()));
    }

    // Parse public key
    let public_key_bytes = parse_ed25519_public_key_pem(public_key_pem)?;
    
    // Create verifying key
    let verifying_key = VerifyingKey::from_bytes(&public_key_bytes)
        .map_err(|e| SpdfError::SignatureError(format!("Invalid public key: {}", e)))?;

    // Validate signature length
    if spdf.signature.len() != SIGNATURE_LENGTH {
        return Err(SpdfError::SignatureError(format!(
            "Invalid signature length: expected {}, got {}",
            SIGNATURE_LENGTH,
            spdf.signature.len()
        )));
    }

    // Hash the unsigned data
    let mut hasher = Sha256::new();
    hasher.update(&spdf.unsigned_data);
    let hash = hasher.finalize();

    // Parse signature
    let sig_bytes: [u8; 64] = spdf.signature[..]
        .try_into()
        .map_err(|_| SpdfError::SignatureError("Invalid signature format".to_string()))?;
    let signature = Signature::from_bytes(&sig_bytes);

    // Verify
    verifying_key
        .verify(&hash, &signature)
        .map_err(|e| SpdfError::SignatureError(format!("Signature verification failed: {}", e)))?;

    Ok(())
}

/// Parse Ed25519 public key from PEM format
///
/// PEM format:
/// -----BEGIN PUBLIC KEY-----
/// <base64-encoded DER>
/// -----END PUBLIC KEY-----
fn parse_ed25519_public_key_pem(pem: &str) -> Result<[u8; 32], SpdfError> {
    // Remove PEM headers and whitespace
    let pem = pem
        .replace("-----BEGIN PUBLIC KEY-----", "")
        .replace("-----END PUBLIC KEY-----", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace(" ", "");

    // Decode base64
    let decoded = general_purpose::STANDARD
        .decode(&pem)
        .map_err(|e| SpdfError::SignatureError(format!("Invalid PEM base64: {}", e)))?;

    // Ed25519 public key in SubjectPublicKeyInfo format is 44 bytes,
    // the last 32 bytes are the actual key
    if decoded.len() < 32 {
        return Err(SpdfError::SignatureError(format!(
            "PEM decoded data too short: {} bytes, expected at least 32",
            decoded.len()
        )));
    }

    let key_bytes: [u8; 32] = decoded[decoded.len() - 32..]
        .try_into()
        .map_err(|_| SpdfError::SignatureError("Invalid key length".to_string()))?;

    Ok(key_bytes)
}

/// Verify signature using a specific public key (not from header)
pub fn verify_signature_with_key(spdf: &SpdfFile, public_key_pem: &str) -> Result<(), SpdfError> {
    let public_key_bytes = parse_ed25519_public_key_pem(public_key_pem)?;
    
    let verifying_key = VerifyingKey::from_bytes(&public_key_bytes)
        .map_err(|e| SpdfError::SignatureError(format!("Invalid public key: {}", e)))?;

    if spdf.signature.len() != SIGNATURE_LENGTH {
        return Err(SpdfError::SignatureError("Invalid signature length".to_string()));
    }

    let mut hasher = Sha256::new();
    hasher.update(&spdf.unsigned_data);
    let hash = hasher.finalize();

    let sig_bytes: [u8; 64] = spdf.signature[..]
        .try_into()
        .map_err(|_| SpdfError::SignatureError("Invalid signature format".to_string()))?;
    let signature = Signature::from_bytes(&sig_bytes);

    verifying_key
        .verify(&hash, &signature)
        .map_err(|e| SpdfError::SignatureError(format!("Signature verification failed: {}", e)))?;

    Ok(())
}

/// Check if an SPDF file is tampered (quick check without full verification)
pub fn is_potentially_tampered(spdf: &SpdfFile) -> bool {
    // Quick checks for obvious tampering
    
    // Check version
    if spdf.version != 0x01 {
        return true;
    }

    // Check signature length
    if spdf.signature.len() != SIGNATURE_LENGTH {
        return true;
    }

    // Check for empty required fields
    if spdf.header.doc_id.is_empty() || spdf.header.server_url.is_empty() {
        return true;
    }

    // Check for empty public key
    if spdf.header.public_key.is_empty() {
        return true;
    }

    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_pem_format() {
        // Valid Ed25519 public key PEM (example, not a real key)
        let valid_pem = "-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAthisisafakepublickeyfortesting123456789
-----END PUBLIC KEY-----";

        // This should parse without error (though the key is fake)
        let result = parse_ed25519_public_key_pem(valid_pem);
        // Result depends on the actual base64 content
    }

    #[test]
    fn test_invalid_pem() {
        let invalid_pem = "not a valid pem";
        let result = parse_ed25519_public_key_pem(invalid_pem);
        assert!(result.is_err());
    }
}
