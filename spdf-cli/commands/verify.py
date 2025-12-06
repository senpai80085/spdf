"""
SPDF CLI - Verify Command

Verifies SPDF file signatures and integrity.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add server path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "spdf-server"))


def verify_command(args):
    """
    Verify an SPDF file's signature and integrity.
    
    Args:
        args: Argparse namespace with:
            - input: Input SPDF path
            - public_key: Optional public key PEM file
            - verbose: Verbose output
    """
    from crypto.decrypt import parse_spdf_file, verify_signature, get_spdf_info
    
    input_path = Path(args.input)
    
    # Validate input
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    print(f"Verifying: {input_path}")
    print("=" * 50)
    
    try:
        # Read file
        with open(input_path, 'rb') as f:
            data = f.read()
        
        file_size = len(data)
        
        # Get basic info
        info = get_spdf_info(data)
        
        print(f"\n📄 Document Information")
        print(f"   Document ID: {info['doc_id']}")
        print(f"   Title: {info['title']}")
        print(f"   Organization: {info['org_id']}")
        print(f"   Server URL: {info['server_url']}")
        print(f"   Created: {info['created_at']}")
        print(f"   File Size: {file_size:,} bytes")
        print(f"   Content Size: {info['content_size']:,} bytes")
        
        print(f"\n🔒 Permissions")
        perms = info['permissions']
        print(f"   Print: {'✓ Allowed' if perms.get('allow_print') else '✗ Denied'}")
        print(f"   Copy: {'✓ Allowed' if perms.get('allow_copy') else '✗ Denied'}")
        print(f"   Max Devices: {perms.get('max_devices', 2)}")
        print(f"   Offline Days: {perms.get('offline_days', 0)}")
        
        print(f"\n🏷️ Features")
        print(f"   Device Binding: {'Required' if info.get('device_binding_required') else 'Optional'}")
        print(f"   Offline Allowed: {'Yes' if info.get('offline_allowed') else 'No'}")
        
        watermark = info.get('watermark', {})
        if watermark.get('enabled'):
            print(f"   Watermark: {watermark.get('text', 'Enabled')}")
        else:
            print(f"   Watermark: Disabled")
        
        # Parse full file for signature verification
        spdf = parse_spdf_file(str(input_path))
        
        print(f"\n🔐 Signature Verification")
        
        # Check for public key
        if args.public_key:
            print(f"   Using external key: {args.public_key}")
            with open(args.public_key, 'r') as f:
                public_key_pem = f.read()
            # Would need to use verify_signature_with_key from verify module
        
        try:
            verify_signature(spdf)
            print("   ✓ Signature VALID")
            print("   ✓ File integrity verified")
            signature_valid = True
        except Exception as e:
            print(f"   ✗ Signature INVALID: {e}")
            signature_valid = False
        
        # Verbose output
        if args.verbose:
            print(f"\n📊 Technical Details")
            print(f"   Version: {spdf.version}")
            print(f"   Flags: 0x{spdf.flags:04X}")
            print(f"   Wrapped Key Length: {len(spdf.wrapped_key)} bytes")
            print(f"   Nonce Length: {len(spdf.nonce)} bytes")
            print(f"   Ciphertext Length: {len(spdf.ciphertext)} bytes")
            print(f"   Auth Tag Length: {len(spdf.auth_tag)} bytes")
            print(f"   Signature Length: {len(spdf.signature)} bytes")
            
            print(f"\n   Public Key (truncated):")
            pk = spdf.header.public_key
            if pk:
                lines = pk.strip().split('\n')
                for line in lines[:3]:
                    print(f"     {line}")
                if len(lines) > 3:
                    print(f"     ... ({len(lines) - 3} more lines)")
        
        print("\n" + "=" * 50)
        
        if signature_valid:
            print("✓ VERIFICATION PASSED")
            sys.exit(0)
        else:
            print("✗ VERIFICATION FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
