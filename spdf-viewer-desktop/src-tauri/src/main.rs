mod auth;
mod spdf;

use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use std::fs;
use tauri::Manager;
use std::sync::Mutex;

// App State to store JWT token
struct AppState {
    auth_token: Mutex<Option<String>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct OpenFileResult {
    success: bool,
    message: String,
    header: Option<spdf::SpdfHeader>,
    pdf_base64: Option<String>,
    needs_login: bool,
    watermark_data: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
struct LoginResult {
    success: bool,
    message: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct KeyResponse {
    k_doc: String, // base64
    permissions: spdf::SpdfPermissions,
    watermark_data: serde_json::Value,
}

#[tauri::command]
async fn login(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    server_url: String,
    license_key: String,
) -> Result<LoginResult, String> {
    println!("Attempting login with license key to: {}", server_url);

    let client = reqwest::Client::new();
    let login_url = format!("{}/auth/login-with-key", server_url.trim_end_matches('/'));

    // Call the license key authentication endpoint
    let res = client
        .post(&login_url)
        .json(&serde_json::json!({
            "license_key": license_key
        }))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;

    if !res.status().is_success() {
        let status = res.status();
        let text = res.text().await.unwrap_or_default();
        return Ok(LoginResult {
            success: false,
            message: format!("Authentication failed: {} - {}", status, text),
        });
    }

    // Parse response
    #[derive(serde::Deserialize)]
    struct LoginResponse {
        access_token: String,
        token_type: String,
        user_email: String,
        doc_id: String,
    }

    let login_res: LoginResponse = res.json().await.map_err(|e| format!("Invalid response: {}", e))?;

    // Store token in memory
    {
        let mut guard = state.auth_token.lock().unwrap();
        *guard = Some(login_res.access_token.clone());
    }

    // Persist token to disk
    let app_dir = app_handle.path().app_data_dir().unwrap();
    if !app_dir.exists() {
        fs::create_dir_all(&app_dir).map_err(|e| format!("Failed to create app dir: {}", e))?;
    }
    let token_path = app_dir.join("token");
    fs::write(token_path, &login_res.access_token).map_err(|e| format!("Failed to save token: {}", e))?;

    println!("Login successful for user: {}", login_res.user_email);

    Ok(LoginResult {
        success: true,
        message: format!("Authenticated as {}", login_res.user_email),
    })
}

#[tauri::command]
async fn open_spdf_file(
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, AppState>,
    file_path: String,
) -> Result<OpenFileResult, String> {
    println!("Opening SPDF file: {}", file_path);

    // 1. Read SPDF file structure
    let spdf_file = spdf::SpdfFile::read(&file_path).map_err(|e| format!("{:?}", e))?;
    println!("SPDF header: {:?}", spdf_file.header);

    // 2. Check for Auth Token
    let token = {
        let guard = state.auth_token.lock().unwrap();
        guard.clone()
    };

    // Try to load from disk if not in memory
    let token = if token.is_none() {
        let app_dir = app_handle.path().app_data_dir().unwrap();
        let token_path = app_dir.join("token");
        if token_path.exists() {
             fs::read_to_string(token_path).ok()
        } else {
            None
        }
    } else {
        token
    };

    if token.is_none() {
        return Ok(OpenFileResult {
            success: false,
            message: "Authentication required".to_string(),
            header: Some(spdf_file.header),
            pdf_base64: None,
            needs_login: true,
            watermark_data: None,
        });
    }
    let token = token.unwrap();

    // 3. Get Device Info
    let device_info = auth::get_device_info(&app_handle).map_err(|e| format!("Device info error: {}", e))?;

    // 4. Fetch Key from Server
    let client = reqwest::Client::new();
    let server_url = spdf_file.header.server_url.trim_end_matches('/');
    let key_url = format!("{}/keys/get", server_url);

    println!("Requesting key from: {}", key_url);

    let res = client
        .post(&key_url)
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "doc_id": spdf_file.header.doc_id,
            "device_id": device_info.device_id,
            "device_name": device_info.device_name
        }))
        .send()
        .await
        .map_err(|e| format!("Network error: {}", e))?;

    if !res.status().is_success() {
        let status = res.status();
        let text = res.text().await.unwrap_or_default();
        
        if status == reqwest::StatusCode::UNAUTHORIZED {
             return Ok(OpenFileResult {
                success: false,
                message: "Session expired. Please login again.".to_string(),
                header: Some(spdf_file.header),
                pdf_base64: None,
                needs_login: true,
                watermark_data: None,
            });
        }

        return Ok(OpenFileResult {
            success: false,
            message: format!("Server denied access: {} - {}", status, text),
            header: Some(spdf_file.header),
            pdf_base64: None,
            needs_login: false,
            watermark_data: None,
        });
    }

    let key_res: KeyResponse = res.json().await.map_err(|e| format!("Invalid server response: {}", e))?;

    // 5. Decode K_doc
    let k_doc_bytes = general_purpose::STANDARD.decode(&key_res.k_doc).map_err(|e| format!("Invalid key encoding: {}", e))?;
    if k_doc_bytes.len() != 32 {
        return Err("Invalid key length from server".to_string());
    }
    let mut k_doc = [0u8; 32];
    k_doc.copy_from_slice(&k_doc_bytes);

    // 6. Verify Signature (using Org Public Key) - Optional for now
    let home_dir = dirs::home_dir().unwrap();
    let public_key_path = home_dir.join(".spdf").join("keys").join(format!("{}_public.pem", spdf_file.header.org_id));
    
    if public_key_path.exists() {
        if let Ok(pem) = fs::read_to_string(public_key_path) {
             if let Err(e) = spdf_file.verify_signature(&pem) {
                 println!("Warning: Signature verification failed: {:?}", e);
                 // Continue anyway for testing
             }
        }
    } else {
        println!("Warning: Public key not found. Skipping signature verification.");
    }

    // 7. Decrypt
    let pdf_bytes = spdf_file.decrypt(&k_doc).map_err(|e| format!("{:?}", e))?;
    let pdf_base64 = general_purpose::STANDARD.encode(&pdf_bytes);

    Ok(OpenFileResult {
        success: true,
        message: "Document opened successfully".to_string(),
        header: Some(spdf_file.header),
        pdf_base64: Some(pdf_base64),
        needs_login: false,
        watermark_data: Some(key_res.watermark_data),
    })
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            auth_token: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![open_spdf_file, login])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
