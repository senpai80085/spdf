// SPDF Viewer Desktop - Main Library
//
// This is the entry point for the Tauri application backend.

// Module declarations
pub mod auth;
pub mod device_id;
pub mod decrypt;
pub mod spdf;
pub mod spdf_parser;
pub mod verify;

use crate::spdf_parser::SpdfFile;
use crate::device_id::{generate_device_hash, get_device_name};
use crate::verify::verify_signature;
use crate::decrypt::decrypt_content_slice;
use serde::{Deserialize, Serialize};

// Response types for Tauri commands
#[derive(Serialize, Deserialize)]
pub struct SpdfInfo {
    pub doc_id: String,
    pub title: String,
    pub org_id: String,
    pub server_url: String,
    pub created_at: String,
    pub allow_print: bool,
    pub allow_copy: bool,
    pub max_devices: u32,
    pub requires_device_binding: bool,
}

#[derive(Serialize, Deserialize)]
pub struct DeviceInfo {
    pub device_hash: String,
    pub device_name: String,
}

#[derive(Serialize, Deserialize)]
pub struct DecryptResult {
    pub success: bool,
    pub pdf_data: Option<Vec<u8>>,
    pub error: Option<String>,
}

// Tauri commands

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn get_spdf_info(file_path: &str) -> Result<SpdfInfo, String> {
    let spdf = SpdfFile::read(file_path).map_err(|e| e.to_string())?;
    
    Ok(SpdfInfo {
        doc_id: spdf.header.doc_id.clone(),
        title: spdf.header.title.clone(),
        org_id: spdf.header.org_id.clone(),
        server_url: spdf.header.server_url.clone(),
        created_at: spdf.header.created_at.clone(),
        allow_print: spdf.header.permissions.allow_print,
        allow_copy: spdf.header.permissions.allow_copy,
        max_devices: spdf.header.permissions.max_devices,
        requires_device_binding: spdf.requires_device_binding(),
    })
}

#[tauri::command]
fn get_device_info() -> Result<DeviceInfo, String> {
    let device_hash = generate_device_hash().map_err(|e| e.to_string())?;
    let device_name = get_device_name();
    
    Ok(DeviceInfo {
        device_hash,
        device_name,
    })
}

#[tauri::command]
fn verify_spdf(file_path: &str) -> Result<bool, String> {
    let spdf = SpdfFile::read(file_path).map_err(|e| e.to_string())?;
    verify_signature(&spdf).map_err(|e| e.to_string())?;
    Ok(true)
}

#[tauri::command]
fn decrypt_spdf(file_path: &str, doc_key_hex: &str) -> Result<DecryptResult, String> {
    // Parse SPDF file
    let spdf = SpdfFile::read(file_path).map_err(|e| e.to_string())?;
    
    // Verify signature first
    if let Err(e) = verify_signature(&spdf) {
        return Ok(DecryptResult {
            success: false,
            pdf_data: None,
            error: Some(format!("Signature verification failed: {}", e)),
        });
    }
    
    // Parse the hex key
    let doc_key = hex::decode(doc_key_hex).map_err(|e| format!("Invalid key hex: {}", e))?;
    
    // Decrypt
    match decrypt_content_slice(&spdf, &doc_key) {
        Ok(pdf_data) => Ok(DecryptResult {
            success: true,
            pdf_data: Some(pdf_data),
            error: None,
        }),
        Err(e) => Ok(DecryptResult {
            success: false,
            pdf_data: None,
            error: Some(e.to_string()),
        }),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            get_spdf_info,
            get_device_info,
            verify_spdf,
            decrypt_spdf
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
