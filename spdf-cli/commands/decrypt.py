"""
SPDF CLI - Decrypt Command

Decrypts SPDF files back to PDF format.
"""

import sys
from pathlib import Path

# Add server path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "spdf-server"))


def decrypt_command(args):
    """
    Decrypt an SPDF file to PDF format.
    
    Args:
        args: Argparse namespace with:
            - input: Input SPDF path
            - output: Output PDF path
            - license: License key (for server mode)
            - key: Document key in hex (for offline mode)
            - no_verify: Skip signature verification
    """
    from crypto.decrypt import decrypt_spdf_file, parse_spdf_file, verify_signature
    from crypto.keys import KeyManager
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Validate input
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    # Check output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Decrypting: {input_path}")
    
    try:
        # Parse the SPDF file first
        spdf = parse_spdf_file(str(input_path))
        
        print(f"  Document ID: {spdf.header.doc_id}")
        print(f"  Organization: {spdf.header.org_id}")
        print(f"  Title: {spdf.header.title}")
        
        # Verify signature unless skipped
        if not args.no_verify:
            print("  Verifying signature...")
            try:
                verify_signature(spdf)
                print("  ✓ Signature valid")
            except Exception as e:
                print(f"  ✗ Signature verification failed: {e}")
                print("\n⚠️  This file may be tampered with!")
                response = input("Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    sys.exit(1)
        
        # Get document key
        if args.key:
            # Offline mode with hex key
            try:
                doc_key = bytes.fromhex(args.key)
                if len(doc_key) != 32:
                    print("Error: Document key must be 32 bytes (64 hex characters)")
                    sys.exit(1)
            except ValueError:
                print("Error: Invalid hex key format")
                sys.exit(1)
                
            # We have the raw key, need to decrypt directly
            from crypto.decrypt import decrypt_content
            pdf_bytes = decrypt_content(spdf, doc_key)
            
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
                
        elif args.license:
            # Server mode with license validation
            print(f"  Using license: {args.license[:15]}...")
            
            # In production, this would call the server API
            # For CLI, we use local key manager if available
            key_manager = KeyManager(spdf.header.org_id)
            
            try:
                # Unwrap the document key
                doc_key = key_manager.unwrap_key(spdf.wrapped_key)
                
                from crypto.decrypt import decrypt_content
                pdf_bytes = decrypt_content(spdf, doc_key)
                
                with open(output_path, 'wb') as f:
                    f.write(pdf_bytes)
                    
            except Exception as e:
                print(f"Error: Could not unwrap key: {e}")
                print("Note: CLI decrypt requires access to the master key")
                sys.exit(1)
        else:
            # Try local key manager
            print("  Using local key manager...")
            
            key_manager = KeyManager(spdf.header.org_id)
            
            try:
                spdf_result = decrypt_spdf_file(
                    input_path=str(input_path),
                    output_path=str(output_path),
                    key_manager=key_manager,
                    verify=not args.no_verify
                )
            except Exception as e:
                print(f"Error: Decryption failed: {e}")
                print("\nProvide either --license or --key to decrypt")
                sys.exit(1)
        
        output_size = output_path.stat().st_size
        
        print(f"\n✓ Decrypted: {output_path}")
        print(f"  Size: {output_size:,} bytes")
        
    except Exception as e:
        print(f"Error: Decryption failed: {e}")
        sys.exit(1)
