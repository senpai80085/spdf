"""
Key Manager for SPDF Server

Manages Ed25519 signing keys for organizations.
Stores keys in ~/.spdf/keys/
"""

import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization


class KeyManager:
    def __init__(self, keys_dir: str = None):
        """
        Initialize Key Manager.
        
        Args:
            keys_dir: Directory to store keys (default: ~/.spdf/keys/)
        """
        if keys_dir is None:
            keys_dir = os.path.join(Path.home(), '.spdf', 'keys')
        
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_key_path(self, org_id: str) -> Path:
        """Get path to private key file for org."""
        return self.keys_dir / f"{org_id}_private.pem"
    
    def _get_public_key_path(self, org_id: str) -> Path:
        """Get path to public key file for org."""
        return self.keys_dir / f"{org_id}_public.pem"
    
    def generate_key(self, org_id: str) -> Ed25519PrivateKey:
        """
        Generate a new Ed25519 key pair for an organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            Ed25519PrivateKey
        """
        # Generate key pair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize and save private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        private_path = self._get_key_path(org_id)
        with open(private_path, 'wb') as f:
            f.write(private_pem)
        
        # Set restricted permissions (owner only)
        os.chmod(private_path, 0o600)
        
        # Serialize and save public key
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        public_path = self._get_public_key_path(org_id)
        with open(public_path, 'wb') as f:
            f.write(public_pem)
        
        print(f"  ✓ Generated new key pair for org: {org_id}")
        print(f"    Private: {private_path}")
        print(f"    Public:  {public_path}")
        
        return private_key
    
    def get_signing_key(self, org_id: str) -> Ed25519PrivateKey:
        """
        Get signing key for an organization (generate if doesn't exist).
        
        Args:
            org_id: Organization ID
        
        Returns:
            Ed25519PrivateKey
        """
        private_path = self._get_key_path(org_id)
        
        # Generate if doesn't exist
        if not private_path.exists():
            return self.generate_key(org_id)
        
        # Load existing key
        with open(private_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
        
        return private_key
    
    def get_public_key_pem(self, org_id: str) -> bytes:
        """
        Get public key PEM for an organization.
        
        Args:
            org_id: Organization ID
        
        Returns:
            Public key as PEM bytes
        """
        public_path = self._get_public_key_path(org_id)
        
        if not public_path.exists():
            raise FileNotFoundError(f"Public key not found for org: {org_id}")
        
        with open(public_path, 'rb') as f:
            return f.read()
    
    def export_public_key(self, org_id: str, output_path: str):
        """
        Export public key to a file.
        
        Args:
            org_id: Organization ID
            output_path: Path to output file
        """
        public_pem = self.get_public_key_pem(org_id)
        
        with open(output_path, 'wb') as f:
            f.write(public_pem)
        
        print(f"  ✓ Public key exported to: {output_path}")
