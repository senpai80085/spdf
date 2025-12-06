#!/usr/bin/env python3
"""
SPDF CLI Tool

Command-line interface for SPDF operations:
- encrypt: Convert PDF to SPDF
- decrypt: Convert SPDF to PDF
- verify: Verify SPDF signature
- license: Manage licenses
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "spdf-server"))

from commands.encrypt import encrypt_command
from commands.decrypt import decrypt_command
from commands.verify import verify_command
from commands.license import license_command


def main():
    parser = argparse.ArgumentParser(
        prog="spdf",
        description="SPDF - Secure PDF Document Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  spdf encrypt input.pdf -o output.spdf --doc-id DOC-001
  spdf decrypt input.spdf -o output.pdf --license SPDF-XXXX-XXXX-XXXX-XXXX
  spdf verify file.spdf
  spdf license add user@example.com --doc DOC-001 --expires 30
  spdf license list
  spdf license revoke SPDF-XXXX-XXXX-XXXX-XXXX
        """
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="spdf 1.0.0"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Encrypt command
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt PDF to SPDF")
    encrypt_parser.add_argument("input", help="Input PDF file")
    encrypt_parser.add_argument("-o", "--output", required=True, help="Output SPDF file")
    encrypt_parser.add_argument("--doc-id", required=True, help="Document ID")
    encrypt_parser.add_argument("--org-id", default="default", help="Organization ID")
    encrypt_parser.add_argument("--title", help="Document title")
    encrypt_parser.add_argument("--server-url", default="http://localhost:8000", help="Server URL")
    encrypt_parser.add_argument("--allow-print", action="store_true", help="Allow printing")
    encrypt_parser.add_argument("--allow-copy", action="store_true", help="Allow copying")
    encrypt_parser.add_argument("--max-devices", type=int, default=2, help="Max devices per license")
    encrypt_parser.add_argument("--offline-days", type=int, default=0, help="Offline access days")
    encrypt_parser.add_argument("--no-watermark", action="store_true", help="Disable watermark")
    
    # Decrypt command
    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt SPDF to PDF")
    decrypt_parser.add_argument("input", help="Input SPDF file")
    decrypt_parser.add_argument("-o", "--output", required=True, help="Output PDF file")
    decrypt_parser.add_argument("--license", help="License key (for server mode)")
    decrypt_parser.add_argument("--key", help="Document key (hex, for offline mode)")
    decrypt_parser.add_argument("--no-verify", action="store_true", help="Skip signature verification")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify SPDF signature")
    verify_parser.add_argument("input", help="Input SPDF file")
    verify_parser.add_argument("--public-key", help="Public key PEM file (optional)")
    verify_parser.add_argument("--verbose", "-V", action="store_true", help="Verbose output")
    
    # License command
    license_parser = subparsers.add_parser("license", help="Manage licenses")
    license_subparsers = license_parser.add_subparsers(dest="license_action", help="License actions")
    
    # license add
    add_parser = license_subparsers.add_parser("add", help="Create new license")
    add_parser.add_argument("email", help="User email")
    add_parser.add_argument("--doc", required=True, help="Document ID")
    add_parser.add_argument("--expires", type=int, help="Expiration in days")
    add_parser.add_argument("--max-devices", type=int, default=2, help="Max devices")
    add_parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    
    # license list
    list_parser = license_subparsers.add_parser("list", help="List licenses")
    list_parser.add_argument("--doc", help="Filter by document ID")
    list_parser.add_argument("--email", help="Filter by email")
    list_parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    
    # license revoke
    revoke_parser = license_subparsers.add_parser("revoke", help="Revoke license")
    revoke_parser.add_argument("license_key", help="License key to revoke")
    revoke_parser.add_argument("--reason", help="Revocation reason")
    revoke_parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    
    # license status
    status_parser = license_subparsers.add_parser("status", help="Get license status")
    status_parser.add_argument("license_key", help="License key")
    status_parser.add_argument("--server", default="http://localhost:8000", help="Server URL")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == "encrypt":
            encrypt_command(args)
        elif args.command == "decrypt":
            decrypt_command(args)
        elif args.command == "verify":
            verify_command(args)
        elif args.command == "license":
            if not args.license_action:
                license_parser.print_help()
                sys.exit(1)
            license_command(args)
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
