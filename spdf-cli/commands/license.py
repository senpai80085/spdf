"""
SPDF CLI - License Command

Manages SPDF licenses via server API.
"""

import sys
import json
import requests
from datetime import datetime

# HTTP timeout
TIMEOUT = 30


def license_command(args):
    """
    Manage licenses via server API.
    
    Args:
        args: Argparse namespace with license_action and related fields
    """
    action = args.license_action
    
    if action == "add":
        add_license(args)
    elif action == "list":
        list_licenses(args)
    elif action == "revoke":
        revoke_license(args)
    elif action == "status":
        license_status(args)
    else:
        print(f"Unknown license action: {action}")
        sys.exit(1)


def add_license(args):
    """Create a new license."""
    server = args.server.rstrip('/')
    url = f"{server}/api/license/create"
    
    print(f"Creating license on {server}")
    print(f"  Email: {args.email}")
    print(f"  Document: {args.doc}")
    print(f"  Max Devices: {args.max_devices}")
    if args.expires:
        print(f"  Expires: {args.expires} days")
    
    payload = {
        "user_email": args.email,
        "doc_id": args.doc,
        "max_devices": args.max_devices,
        "expires_days": args.expires
    }
    
    try:
        # Note: In production, this requires authentication
        headers = {"X-Admin-Token": "admin-token-placeholder"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ License Created Successfully!")
            print(f"\n  License Key: {data.get('license_key')}")
            print(f"  User: {data.get('user_email')}")
            print(f"  Document: {data.get('doc_id')}")
            print(f"  Max Devices: {data.get('max_devices')}")
            if data.get('expires_at'):
                print(f"  Expires: {data.get('expires_at')}")
            print(f"\n📋 Copy this license key and share with the user.")
        else:
            print(f"Error: Server returned {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {server}")
        print("Make sure the SPDF server is running.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def list_licenses(args):
    """List licenses with optional filters."""
    server = args.server.rstrip('/')
    url = f"{server}/api/license/list"
    
    params = {}
    if args.doc:
        params["doc_id"] = args.doc
    if args.email:
        params["user_email"] = args.email
    
    print(f"Fetching licenses from {server}")
    if params:
        print(f"  Filters: {params}")
    
    try:
        headers = {"X-Admin-Token": "admin-token-placeholder"}
        
        response = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            licenses = data.get("licenses", [])
            
            if not licenses:
                print("\nNo licenses found.")
                return
            
            print(f"\n📋 Licenses ({len(licenses)} total)")
            print("-" * 70)
            
            for lic in licenses:
                print(f"  {lic.get('license_key')}")
                print(f"    User: {lic.get('user_email')}")
                print(f"    Document: {lic.get('doc_id')}")
                print(f"    Status: {lic.get('status', 'active')}")
                print(f"    Devices: {lic.get('used_devices', 0)}/{lic.get('max_devices', 2)}")
                if lic.get('expires_at'):
                    print(f"    Expires: {lic.get('expires_at')}")
                print()
        else:
            print(f"Error: Server returned {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {server}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def revoke_license(args):
    """Revoke a license."""
    server = args.server.rstrip('/')
    url = f"{server}/api/license/revoke"
    
    print(f"Revoking license: {args.license_key}")
    if args.reason:
        print(f"  Reason: {args.reason}")
    
    payload = {
        "license_key": args.license_key,
        "reason": args.reason
    }
    
    try:
        headers = {"X-Admin-Token": "admin-token-placeholder"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ License Revoked Successfully!")
            print(f"  License: {data.get('license_key')}")
            print(f"  Revoked At: {data.get('revoked_at')}")
            if data.get('reason'):
                print(f"  Reason: {data.get('reason')}")
        else:
            print(f"Error: Server returned {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {server}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def license_status(args):
    """Get license status."""
    server = args.server.rstrip('/')
    license_key = args.license_key
    url = f"{server}/api/license/status/{license_key}"
    
    print(f"Checking license: {license_key}")
    
    try:
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📋 License Status")
            print("-" * 50)
            print(f"  License Key: {data.get('license_key')}")
            print(f"  Status: {data.get('status', 'unknown').upper()}")
            print(f"  User: {data.get('user_email')}")
            print(f"  Document: {data.get('doc_id')}")
            print(f"  Devices: {data.get('used_devices', 0)}/{data.get('max_devices', 2)}")
            print(f"  Created: {data.get('created_at')}")
            
            if data.get('expires_at'):
                print(f"  Expires: {data.get('expires_at')}")
                # Check if expired
                try:
                    exp = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                    if exp < datetime.now(exp.tzinfo):
                        print("  ⚠️  LICENSE EXPIRED")
                except:
                    pass
            else:
                print("  Expires: Never")
                
        elif response.status_code == 404:
            print(f"\n✗ License not found: {license_key}")
            sys.exit(1)
        else:
            print(f"Error: Server returned {response.status_code}")
            print(response.text)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to server at {server}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
