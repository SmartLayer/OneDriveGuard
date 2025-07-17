#!/usr/bin/env python3
"""
OneDrive ACL Lister - Using rclone.conf token to access Microsoft Graph API directly.

This script demonstrates how to:
1. Read the OAuth token from rclone.conf
2. Use it to make direct Microsoft Graph API calls
3. List ACL (Access Control List) for a specific OneDrive item

Prerequisites:
- rclone must be installed and configured with OneDrive remote
- requests library (pip install requests)
- Valid OAuth token in ~/.config/rclone/rclone.conf

Usage:
    python acl_demo.py <item_path> [remote_name]
    
    item_path: Required. Path to the folder or file in OneDrive (e.g., "Documents", "Documents/file.txt")
    remote_name: Optional. Name of the OneDrive remote (default: OneDrive)

Example:
    python acl_demo.py "Documents"
    python acl_demo.py "Documents/Project" "MyOneDrive"
    python acl_demo.py "file.txt"
"""

import requests
import json
import sys
import argparse
import configparser
import os
from typing import Dict, List, Optional

def get_access_token(rclone_remote: str = "OneDrive") -> Optional[str]:
    """
    Extract access token from rclone.conf for the specified remote.
    
    Args:
        rclone_remote: Name of the OneDrive remote in rclone.conf
        
    Returns:
        Access token string if successful, None otherwise
    """
    conf_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    if not os.path.exists(conf_path):
        print(f"Error: rclone config not found at {conf_path}")
        print("Please configure rclone first: rclone config")
        return None
    
    config = configparser.ConfigParser()
    config.read(conf_path)
    
    if rclone_remote not in config:
        print(f"Error: Remote '{rclone_remote}' not found in {conf_path}")
        print(f"Available remotes: {list(config.sections())}")
        return None
    
    section = config[rclone_remote]
    token_json = section.get("token")
    if not token_json:
        print(f"Error: No token found for remote '{rclone_remote}' in {conf_path}")
        print("Please authenticate first: rclone authorize onedrive")
        return None
    
    try:
        token = json.loads(token_json)
    except Exception as e:
        print(f"Error: Could not parse token JSON: {e}")
        return None
    
    access_token = token.get("access_token")
    if not access_token:
        print("Error: No access_token in token JSON")
        print("Token may be expired. Please re-authenticate: rclone authorize onedrive")
        return None
    
    return access_token

def list_item_acl(item_path: str, rclone_remote: str = "OneDrive") -> None:
    """
    List ACL (Access Control List) for a specific OneDrive item.
    
    Args:
        item_path: Path to the folder or file in OneDrive
        rclone_remote: Name of the OneDrive remote in rclone.conf
    """
    print(f"=== OneDrive ACL Lister ===")
    print(f"Item: {item_path}")
    print(f"Remote: {rclone_remote}")
    print()
    
    # Get access token
    access_token = get_access_token(rclone_remote)
    if not access_token:
        return
    
    print("✅ Successfully extracted access token from rclone.conf")
    
    # Make Microsoft Graph API call to get item info
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get item by path
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{item_path}"
    print(f"Getting item info from: {url}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Failed to get item info: {resp.status_code}")
            print(f"Response: {resp.text}")
            return
        
        item_data = resp.json()
        item_id = item_data.get('id')
        if not item_id:
            print("❌ No item ID found in response")
            return
        
        item_name = item_data.get('name', 'Unknown')
        item_type = 'folder' if 'folder' in item_data else 'file'
        print(f"✅ Found {item_type}: {item_name} (ID: {item_id})")
        
        # Now get permissions for this item
        permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
        print(f"\nGetting ACL from: {permissions_url}")
        
        resp = requests.get(permissions_url, headers=headers, timeout=30)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            permissions_data = resp.json()
            permissions = permissions_data.get("value", [])
            
            if permissions:
                print(f"\n✅ Found {len(permissions)} permission(s) in ACL:")
                print("=" * 60)
                
                for i, perm in enumerate(permissions, 1):
                    print(f"\nPermission {i}:")
                    print(f"  ID: {perm.get('id', 'N/A')}")
                    print(f"  Roles: {', '.join(perm.get('roles', []))}")
                    
                    # Check for grantedTo (OneDrive Personal)
                    granted_to = perm.get('grantedTo')
                    if granted_to and granted_to.get('user'):
                        user = granted_to['user']
                        print(f"  User: {user.get('displayName', 'N/A')} ({user.get('id', 'N/A')})")
                        print(f"  Email: {user.get('email', 'N/A')}")
                    
                    # Check for grantedToIdentities (OneDrive Business)
                    granted_to_identities = perm.get('grantedToIdentities', [])
                    if granted_to_identities:
                        for identity in granted_to_identities:
                            if identity.get('user'):
                                user = identity['user']
                                print(f"  User: {user.get('displayName', 'N/A')} ({user.get('id', 'N/A')})")
                                print(f"  Email: {user.get('email', 'N/A')}")
                    
                    # Check for link information
                    link = perm.get('link')
                    if link:
                        print(f"  Link Type: {link.get('type', 'N/A')}")
                        print(f"  Link Scope: {link.get('scope', 'N/A')}")
                        print(f"  Link URL: {link.get('webUrl', 'N/A')}")
                    
                    # Additional permission details
                    if perm.get('hasPassword'):
                        print(f"  Password Protected: Yes")
                    
                    if perm.get('expirationDateTime'):
                        print(f"  Expires: {perm.get('expirationDateTime')}")
                    
                    print("-" * 40)
            else:
                print("ℹ️  No permissions found for this item (empty ACL)")
                
        elif resp.status_code == 403:
            print("❌ Access denied - you may not have permission to view ACL for this item")
            print("This could be due to:")
            print("  - Insufficient permissions on the item")
            print("  - Item is in a shared folder you don't own")
            print("  - Microsoft Graph API permissions not granted")
        else:
            print(f"❌ Failed to get ACL: {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="List ACL for OneDrive items using rclone.conf token")
    parser.add_argument("item_path", 
                       help="Path to the folder or file in OneDrive (e.g., 'Documents', 'Documents/file.txt')")
    parser.add_argument("remote", nargs="?", default="OneDrive", 
                       help="Name of the OneDrive remote (default: OneDrive)")
    
    args = parser.parse_args()
    
    print("OneDrive ACL Lister")
    print("=" * 50)
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ requests library not found")
        print("Please install it: pip install requests")
        return
    
    # List ACL for the specified item
    list_item_acl(args.item_path, args.remote)
    
    print("\n=== ACL Listing Complete ===")
    print("This demonstrates direct access to OneDrive ACL via Microsoft Graph API")
    print("using the OAuth token from rclone.conf.")

if __name__ == "__main__":
    main()
