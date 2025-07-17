#!/usr/bin/env python3
"""
OneDrive Direct API Demo - Using rclone.conf token to access Microsoft Graph API directly.

This script demonstrates how to:
1. Read the OAuth token from rclone.conf
2. Use it to make direct Microsoft Graph API calls
3. List files and folders in OneDrive

Prerequisites:
- rclone must be installed and configured with OneDrive remote
- requests library (pip install requests)
- Valid OAuth token in ~/.config/rclone/rclone.conf

Usage:
    python onedrive_permissions_demo.py [remote_name]
    
    If no remote_name is provided, "OneDrive" will be used.

Example:
    python onedrive_permissions_demo.py "OneDrive"
    python onedrive_permissions_demo.py "MyOneDrive"
"""

import requests
import json
import sys
import argparse
import configparser
import os
from typing import Dict, List, Optional

def msgraph_demo_list_files(rclone_remote: str = "OneDrive") -> None:
    """
    Demo: Use the rclone.conf token to list files in OneDrive root via Microsoft Graph API directly.
    
    Args:
        rclone_remote: Name of the OneDrive remote in rclone.conf
    """
    print(f"=== Microsoft Graph API Direct Demo ===")
    print(f"Using remote: {rclone_remote}")
    
    # Read rclone config
    conf_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    if not os.path.exists(conf_path):
        print(f"Error: rclone config not found at {conf_path}")
        print("Please configure rclone first: rclone config")
        return
    
    config = configparser.ConfigParser()
    config.read(conf_path)
    
    if rclone_remote not in config:
        print(f"Error: Remote '{rclone_remote}' not found in {conf_path}")
        print(f"Available remotes: {list(config.sections())}")
        return
    
    section = config[rclone_remote]
    token_json = section.get("token")
    if not token_json:
        print(f"Error: No token found for remote '{rclone_remote}' in {conf_path}")
        print("Please authenticate first: rclone authorize onedrive")
        return
    
    try:
        token = json.loads(token_json)
    except Exception as e:
        print(f"Error: Could not parse token JSON: {e}")
        return
    
    access_token = token.get("access_token")
    if not access_token:
        print("Error: No access_token in token JSON")
        print("Token may be expired. Please re-authenticate: rclone authorize onedrive")
        return
    
    print("✅ Successfully extracted access token from rclone.conf")
    
    # Make Microsoft Graph API call to list files in root
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    
    print(f"\nMaking Microsoft Graph API call to: {url}")
    print("Headers: Authorization: Bearer [TOKEN]")
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("value", [])
            print(f"\n✅ Success! Found {len(items)} items in OneDrive root:")
            print()
            
            for item in items:
                name = item.get('name', 'Unknown')
                item_type = '📁 folder' if 'folder' in item else '📄 file'
                size = item.get('size', 0)
                size_str = f"{size:,} bytes" if size > 0 else "N/A"
                print(f"  {item_type} {name} ({size_str})")
                
        elif resp.status_code == 401:
            print("❌ Authentication failed - token may be expired")
            print("Please re-authenticate: rclone authorize onedrive")
            print(f"Response: {resp.text}")
            
        else:
            print(f"❌ API call failed with status {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def msgraph_demo_get_permissions(rclone_remote: str = "OneDrive", item_path: str = "") -> None:
    """
    Demo: Get permissions for a specific item using Microsoft Graph API.
    
    Args:
        rclone_remote: Name of the OneDrive remote in rclone.conf
        item_path: Path to the item (empty for root)
    """
    print(f"\n=== Microsoft Graph API Permissions Demo ===")
    print(f"Getting permissions for: {item_path if item_path else 'root'}")
    
    # Read rclone config (same as above)
    conf_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    config = configparser.ConfigParser()
    config.read(conf_path)
    
    if rclone_remote not in config:
        print(f"Error: Remote '{rclone_remote}' not found")
        return
    
    token_json = config[rclone_remote].get("token")
    if not token_json:
        print(f"Error: No token found for remote '{rclone_remote}'")
        return
    
    try:
        token = json.loads(token_json)
        access_token = token.get("access_token")
        if not access_token:
            print("Error: No access_token in token")
            return
    except Exception as e:
        print(f"Error parsing token: {e}")
        return
    
    # First, get the item ID
    headers = {"Authorization": f"Bearer {access_token}"}
    
    if item_path:
        # Get item by path
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{item_path}"
    else:
        # Get root
        url = "https://graph.microsoft.com/v1.0/me/drive/root"
    
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
        
        print(f"✅ Found item ID: {item_id}")
        
        # Now get permissions for this item
        permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
        print(f"\nGetting permissions from: {permissions_url}")
        
        resp = requests.get(permissions_url, headers=headers, timeout=30)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            permissions_data = resp.json()
            permissions = permissions_data.get("value", [])
            
            if permissions:
                print(f"\n✅ Found {len(permissions)} permission(s):")
                print()
                
                for i, perm in enumerate(permissions, 1):
                    print(f"Permission {i}:")
                    print(f"  ID: {perm.get('id', 'N/A')}")
                    print(f"  Roles: {', '.join(perm.get('roles', []))}")
                    
                    # Check for grantedTo (OneDrive Personal)
                    granted_to = perm.get('grantedTo')
                    if granted_to and granted_to.get('user'):
                        user = granted_to['user']
                        print(f"  User: {user.get('displayName', 'N/A')} ({user.get('id', 'N/A')})")
                    
                    # Check for grantedToIdentities (OneDrive Business)
                    granted_to_identities = perm.get('grantedToIdentities', [])
                    if granted_to_identities:
                        for identity in granted_to_identities:
                            if identity.get('user'):
                                user = identity['user']
                                print(f"  User: {user.get('displayName', 'N/A')} ({user.get('id', 'N/A')})")
                    
                    # Check for link information
                    link = perm.get('link')
                    if link:
                        print(f"  Link Type: {link.get('type', 'N/A')}")
                        print(f"  Link Scope: {link.get('scope', 'N/A')}")
                        print(f"  Link URL: {link.get('webUrl', 'N/A')}")
                    
                    print()
            else:
                print("ℹ️  No permissions found for this item")
                
        elif resp.status_code == 403:
            print("❌ Access denied - you may not have permission to view permissions for this item")
        else:
            print(f"❌ Failed to get permissions: {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="OneDrive Direct API Demo using rclone.conf token")
    parser.add_argument("remote", nargs="?", default="OneDrive", 
                       help="Name of the OneDrive remote (default: OneDrive)")
    parser.add_argument("--permissions", metavar="PATH", 
                       help="Get permissions for a specific path (e.g., 'Documents')")
    
    args = parser.parse_args()
    
    print("OneDrive Direct API Demo")
    print("=" * 50)
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ requests library not found")
        print("Please install it: pip install requests")
        return
    
    # Demo 1: List files
    msgraph_demo_list_files(args.remote)
    
    # Demo 2: Get permissions (if requested)
    if args.permissions is not None:
        msgraph_demo_get_permissions(args.remote, args.permissions)
    
    print("\n=== Demo Complete ===")
    print("This demonstrates that we can access Microsoft Graph API directly")
    print("using the OAuth token from rclone.conf, bypassing rclone entirely.")

if __name__ == "__main__":
    main()
