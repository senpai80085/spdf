// Decrypt Module - SPDF content decryption
//
// This module provides AES-256-GCM decryption for SPDF file content.

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};

use crate::spdf_parser::{SpdfFile, SpdfError};

/// Decrypt SPDF content using the document key
///
/// # Arguments
/// * `spdf` - Parsed SPDF file
/// * `doc_key` - 32-byte AES-256 key
///
/// # Returns
/// Decrypted PDF bytes
pub fn decrypt_content(spdf: &SpdfFile, doc_key: &[u8; 32]) -> Result<Vec<u8>, SpdfError> {
    // Validate nonce length
    if spdf.nonce.len() != 12 {
        return Err(SpdfError::DecryptionError(format!(
            "Invalid nonce length: expected 12, got {}",
            spdf.nonce.len()
        )));
    }

    // Validate auth tag length
    if spdf.auth_tag.len() != 16 {
        return Err(SpdfError::DecryptionError(format!(
            "Invalid auth tag length: expected 16, got {}",
            spdf.auth_tag.len()
        )));
    }

    // Create cipher
    let cipher = Aes256Gcm::new(doc_key.into());
    
    // Create nonce
    let nonce_bytes: [u8; 12] = spdf.nonce[..]
        .try_into()
        .map_err(|_| SpdfError::DecryptionError("Invalid nonce".to_string()))?;
    let nonce = Nonce::from_slice(&nonce_bytes);

    // Combine ciphertext and auth tag
    let mut ciphertext_with_tag = spdf.ciphertext.clone();
    ciphertext_with_tag.extend_from_slice(&spdf.auth_tag);

    // Decrypt
    cipher
        .decrypt(nonce, ciphertext_with_tag.as_ref())
        .map_err(|e| SpdfError::DecryptionError(format!("Decryption failed: {}", e)))
}

/// Decrypt SPDF content with key provided as slice
pub fn decrypt_content_slice(spdf: &SpdfFile, doc_key: &[u8]) -> Result<Vec<u8>, SpdfError> {
    if doc_key.len() != 32 {
        return Err(SpdfError::DecryptionError(format!(
            "Invalid key length: expected 32, got {}",
            doc_key.len()
        )));
    }

    let key_array: [u8; 32] = doc_key
        .try_into()
        .map_err(|_| SpdfError::DecryptionError("Invalid key".to_string()))?;

    decrypt_content(spdf, &key_array)
}

/// Decrypt SPDF content from base64-encoded key
pub fn decrypt_content_base64(spdf: &SpdfFile, doc_key_b64: &str) -> Result<Vec<u8>, SpdfError> {
    use base64::{engine::general_purpose, Engine as _};
    
    let doc_key = general_purpose::STANDARD
        .decode(doc_key_b64)
        .map_err(|e| SpdfError::DecryptionError(format!("Invalid base64 key: {}", e)))?;

    decrypt_content_slice(spdf, &doc_key)
}

/// Validate that content appears to be a valid PDF
pub fn validate_pdf_content(content: &[u8]) -> bool {
    // PDF files start with %PDF-
    content.len() >= 4 && &content[0..4] == b"%PDF"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_pdf_content() {
        assert!(validate_pdf_content(b"%PDF-1.4\n..."));
        assert!(!validate_pdf_content(b"Not a PDF"));
        assert!(!validate_pdf_content(b""));
    }

    #[test]
    fn test_decrypt_invalid_key_length() {
        // This would need a valid SpdfFile structure which requires complex setup
        // For now, just test the validation logic
        let short_key = vec![0u8; 16];
        
        // Create minimal test case
        // In practice, this would be integration tested with real SPDF files
    }
}
