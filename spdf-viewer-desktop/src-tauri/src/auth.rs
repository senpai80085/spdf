use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;
use tauri::Manager;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DeviceInfo {
    pub device_id: String,
    pub device_name: String,
}

pub fn get_device_info(app_handle: &tauri::AppHandle) -> Result<DeviceInfo, String> {
    let app_dir = app_handle
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;

    if !app_dir.exists() {
        fs::create_dir_all(&app_dir).map_err(|e| format!("Failed to create app dir: {}", e))?;
    }

    let device_id_path = app_dir.join("device_id");
    let salt_path = app_dir.join("device_salt");

    // 1. Get or create salt
    let salt = if salt_path.exists() {
        fs::read_to_string(&salt_path).map_err(|e| format!("Failed to read salt: {}", e))?
    } else {
        let new_salt = uuid::Uuid::new_v4().to_string();
        fs::write(&salt_path, &new_salt).map_err(|e| format!("Failed to write salt: {}", e))?;
        new_salt
    };

    // 2. Get hardware UUID (simplified for now, using machine-uid crate logic or similar would be better but keeping it simple/standard lib based where possible or using a crate if added)
    // For a robust implementation, we'd use a crate like `machine-uid`.
    // Since I didn't add `machine-uid` to Cargo.toml yet, I will use a placeholder or simple file-based persistence for now, 
    // but the plan called for hardware UUID.
    // Let's try to get a stable system identifier if possible, or fallback to a persistent random ID if not easily accessible without extra crates.
    // Actually, I can use `sys_info` or similar if I added it. I added `dirs`.
    // Let's stick to the plan: "Hardware UUID extraction (platform-specific...)"
    // Without adding more crates, I'll simulate it by reading a system file or command, but that's flaky cross-platform in Rust without a crate.
    // I'll stick to a persistent random UUID + Salt for V1 stability if I can't easily get hardware ID, 
    // BUT the user specifically asked for hardware UUID.
    // I will add `machine-uid` to Cargo.toml to do this properly.
    
    // For now, let's assume I'll add `machine-uid` to Cargo.toml in the next step.
    // Wait, I can't easily add a crate and use it in the same turn without re-compiling.
    // I'll implement a "best effort" hardware ID using `whoami` + hostname for now, combined with the salt.
    // Or better, I'll just use the persistent salt as the "device identity" for this iteration to ensure it works, 
    // and we can upgrade to real hardware ID if I add the crate.
    // Actually, the plan said: "device_id = SHA256(hardware_uuid + local_salt)"
    
    // Let's implement a simple platform-specific command runner to get UUID.
    let hardware_uuid = get_platform_uuid().unwrap_or_else(|_| "UNKNOWN_HARDWARE".to_string());

    // 3. Compute Device ID
    let mut hasher = Sha256::new();
    hasher.update(hardware_uuid.as_bytes());
    hasher.update(salt.as_bytes());
    let result = hasher.finalize();
    let device_id = hex::encode(result);

    // 4. Get Device Name (Hostname)
    let device_name = hostname::get()
        .map(|h| h.to_string_lossy().into_owned())
        .unwrap_or_else(|_| "Unknown Device".to_string());

    Ok(DeviceInfo {
        device_id,
        device_name,
    })
}

#[cfg(target_os = "windows")]
fn get_platform_uuid() -> Result<String, String> {
    use std::process::Command;
    let output = Command::new("wmic")
        .args(&["csproduct", "get", "UUID"])
        .output()
        .map_err(|e| e.to_string())?;
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    // Parse UUID from output (e.g. "UUID \n XXXXXXXX-XXXX-...")
    stdout.lines()
        .nth(1)
        .map(|s| s.trim().to_string())
        .ok_or_else(|| "Failed to parse UUID".to_string())
}

#[cfg(target_os = "linux")]
fn get_platform_uuid() -> Result<String, String> {
    fs::read_to_string("/etc/machine-id")
        .or_else(|_| fs::read_to_string("/var/lib/dbus/machine-id"))
        .map(|s| s.trim().to_string())
        .map_err(|e| e.to_string())
}

#[cfg(target_os = "macos")]
fn get_platform_uuid() -> Result<String, String> {
    use std::process::Command;
    let output = Command::new("ioreg")
        .args(&["-rd1", "-c", "IOPlatformExpertDevice"])
        .output()
        .map_err(|e| e.to_string())?;
    
    let stdout = String::from_utf8_lossy(&output.stdout);
    // Look for "IOPlatformUUID" = "..."
    for line in stdout.lines() {
        if line.contains("IOPlatformUUID") {
            let parts: Vec<&str> = line.split('=').collect();
            if parts.len() >= 2 {
                return Ok(parts[1].trim().trim_matches('"').to_string());
            }
        }
    }
    Err("UUID not found".to_string())
}

#[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
fn get_platform_uuid() -> Result<String, String> {
    Ok("GENERIC_PLATFORM".to_string())
}
