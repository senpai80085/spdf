"""
SPDF CLI - Encrypt Command

Converts PDF files to encrypted SPDF format.
"""

import sys
from pathlib import Path

# Add server path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "spdf-server"))


def encrypt_command(args):
    """
    Encrypt a PDF file to SPDF format.
    
    Args:
        args: Argparse namespace with:
            - input: Input PDF path
            - output: Output SPDF path
            - doc_id: Document ID
            - org_id: Organization ID
            - title: Document title
            - server_url: Server URL
            - allow_print: Allow printing
            - allow_copy: Allow copying
            - max_devices: Max devices
            - offline_days: Offline access days
            - no_watermark: Disable watermark
    """
    from crypto.encrypt import create_spdf_file
    from crypto.keys import KeyManager
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Validate input
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.pdf':
        print("Warning: Input file does not have .pdf extension")
    
    # Check output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Encrypting: {input_path}")
    print(f"  Document ID: {args.doc_id}")
    print(f"  Organization: {args.org_id}")
    print(f"  Server URL: {args.server_url}")
    
    try:
        # Get key manager
        key_manager = KeyManager(args.org_id)
        
        # Create SPDF
        wrapped_key = create_spdf_file(
            input_path=str(input_path),
            output_path=str(output_path),
            doc_id=args.doc_id,
            org_id=args.org_id,
            server_url=args.server_url,
            title=args.title or args.doc_id,
            allow_print=args.allow_print,
            allow_copy=args.allow_copy,
            max_devices=args.max_devices,
            offline_days=getattr(args, 'offline_days', 0),
            watermark_enabled=not getattr(args, 'no_watermark', False)
        )
        
        output_size = output_path.stat().st_size
        
        print(f"\n✓ Created: {output_path}")
        print(f"  Size: {output_size:,} bytes")
        print(f"  Wrapped Key: {wrapped_key.hex()[:32]}...")
        
        # In production, the wrapped key should be stored in the database
        print("\n⚠️  Store the wrapped key in your database!")
        print(f"    Full key: {wrapped_key.hex()}")
        
    except Exception as e:
        print(f"Error: Encryption failed: {e}")
        sys.exit(1)
