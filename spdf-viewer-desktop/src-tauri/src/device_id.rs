// Device ID Module - Hardware fingerprinting for device binding
//
// This module generates a deterministic device hash from hardware information
// that can be used to bind licenses to specific devices.

use sha2::{Sha256, Digest};
use sysinfo::System;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[cfg(target_os = "windows")]
use winreg::enums::*;
#[cfg(target_os = "windows")]
use winreg::RegKey;

/// Error type for device ID operations
#[derive(Debug)]
pub enum DeviceIdError {
    SystemInfoError(String),
    HashError(String),
}

impl std::fmt::Display for DeviceIdError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DeviceIdError::SystemInfoError(msg) => write!(f, "System info error: {}", msg),
            DeviceIdError::HashError(msg) => write!(f, "Hash error: {}", msg),
        }
    }
}

impl std::error::Error for DeviceIdError {}

/// Hardware information collected for fingerprinting
#[derive(Debug, Clone)]
pub struct HardwareInfo {
    pub cpu_id: String,
    pub os_info: String,
    pub machine_id: String,
    pub hostname: String,
}

impl HardwareInfo {
    /// Collect hardware information from the system
    pub fn collect() -> Result<Self, DeviceIdError> {
        let mut sys = System::new_all();
        sys.refresh_all();

        // Get CPU information
        let cpu_id = sys.cpus()
            .first()
            .map(|cpu| format!("{}-{}", cpu.brand(), cpu.vendor_id()))
            .unwrap_or_else(|| "unknown-cpu".to_string());

        // Get OS information
        let os_info = format!(
            "{}-{}-{}",
            System::name().unwrap_or_default(),
            System::os_version().unwrap_or_default(),
            System::kernel_version().unwrap_or_default()
        );

        // Get machine ID (platform-specific)
        let machine_id = get_machine_id().unwrap_or_else(|_| "unknown-machine".to_string());

        // Get hostname
        let hostname = System::host_name().unwrap_or_else(|| "unknown-host".to_string());

        Ok(HardwareInfo {
            cpu_id,
            os_info,
            machine_id,
            hostname,
        })
    }
}

/// Get machine-specific ID based on platform
#[cfg(target_os = "windows")]
fn get_machine_id() -> Result<String, DeviceIdError> {
    // Try to get Windows Machine GUID
    let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
    
    if let Ok(key) = hklm.open_subkey("SOFTWARE\\Microsoft\\Cryptography") {
        if let Ok(guid) = key.get_value::<String, _>("MachineGuid") {
            return Ok(guid);
        }
    }
    
    // Fallback to product ID
    if let Ok(key) = hklm.open_subkey("SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion") {
        if let Ok(product_id) = key.get_value::<String, _>("ProductId") {
            return Ok(product_id);
        }
    }
    
    Err(DeviceIdError::SystemInfoError("Could not get Windows machine ID".to_string()))
}

#[cfg(target_os = "linux")]
fn get_machine_id() -> Result<String, DeviceIdError> {
    // Try /etc/machine-id first
    if let Ok(id) = std::fs::read_to_string("/etc/machine-id") {
        return Ok(id.trim().to_string());
    }
    
    // Try /var/lib/dbus/machine-id
    if let Ok(id) = std::fs::read_to_string("/var/lib/dbus/machine-id") {
        return Ok(id.trim().to_string());
    }
    
    Err(DeviceIdError::SystemInfoError("Could not get Linux machine ID".to_string()))
}

#[cfg(target_os = "macos")]
fn get_machine_id() -> Result<String, DeviceIdError> {
    use std::process::Command;
    
    // Get hardware UUID via ioreg
    let output = Command::new("ioreg")
        .args(["-rd1", "-c", "IOPlatformExpertDevice"])
        .output()
        .map_err(|e| DeviceIdError::SystemInfoError(e.to_string()))?;
    
    let result = String::from_utf8_lossy(&output.stdout);
    
    for line in result.lines() {
        if line.contains("IOPlatformUUID") {
            if let Some(uuid) = line.split('"').nth(3) {
                return Ok(uuid.to_string());
            }
        }
    }
    
    Err(DeviceIdError::SystemInfoError("Could not get macOS hardware UUID".to_string()))
}

#[cfg(not(any(target_os = "windows", target_os = "linux", target_os = "macos")))]
fn get_machine_id() -> Result<String, DeviceIdError> {
    // For other platforms, use a hash of system info
    let mut hasher = DefaultHasher::new();
    System::host_name().hash(&mut hasher);
    Ok(format!("{:016x}", hasher.finish()))
}

/// Salt for device fingerprinting (should match server)
const DEVICE_SALT: &[u8] = b"spdf_device_salt_v1";

/// Generate a deterministic device hash from hardware info
pub fn generate_device_hash() -> Result<String, DeviceIdError> {
    let info = HardwareInfo::collect()?;
    
    let mut hasher = Sha256::new();
    
    // Add salt
    hasher.update(DEVICE_SALT);
    
    // Add hardware info components
    hasher.update(info.cpu_id.as_bytes());
    hasher.update(b":");
    hasher.update(info.machine_id.as_bytes());
    hasher.update(b":");
    hasher.update(info.os_info.as_bytes());
    
    let result = hasher.finalize();
    Ok(hex::encode(result))
}

/// Get a human-readable device name
pub fn get_device_name() -> String {
    let hostname = System::host_name().unwrap_or_else(|| "Unknown".to_string());
    let os = System::name().unwrap_or_else(|| "Unknown OS".to_string());
    format!("{} ({})", hostname, os)
}

/// Verify that the current device matches a given hash
pub fn verify_device_hash(expected_hash: &str) -> Result<bool, DeviceIdError> {
    let current_hash = generate_device_hash()?;
    Ok(current_hash == expected_hash)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hardware_info_collection() {
        let info = HardwareInfo::collect();
        assert!(info.is_ok());
        
        let info = info.unwrap();
        assert!(!info.cpu_id.is_empty());
        assert!(!info.os_info.is_empty());
    }

    #[test]
    fn test_device_hash_generation() {
        let hash1 = generate_device_hash();
        assert!(hash1.is_ok());
        
        let hash1 = hash1.unwrap();
        assert_eq!(hash1.len(), 64); // SHA-256 hex = 64 chars
        
        // Hash should be deterministic
        let hash2 = generate_device_hash().unwrap();
        assert_eq!(hash1, hash2);
    }

    #[test]
    fn test_device_name() {
        let name = get_device_name();
        assert!(!name.is_empty());
    }
}
