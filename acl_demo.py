#!/usr/bin/env python3
"""
OneDrive ACL Manager - Using rclone.conf token to access Microsoft Graph API directly.

This script demonstrates how to:
1. Read the OAuth token from rclone.conf
2. Use it to make direct Microsoft Graph API calls
3. List, invite, and remove ACL (Access Control List) for a specific OneDrive item

Prerequisites:
- rclone must be installed and configured with OneDrive remote
- requests library (pip install requests)
- Valid OAuth token in ~/.config/rclone/rclone.conf

Usage:
    python acl_demo.py <command> [options]
    
Commands:
    list <item_path> [remote_name]     - List ACL for the specified item
    invite <email> <folder_path>... [remote_name]  - Send invitation with editing permission to multiple folders (Personal OneDrive)
    remove <item_path> <email> [remote_name] - Remove all permissions for the email
    
Examples:
    python acl_demo.py list "Documents"
    python acl_demo.py invite amanuensis@weiwu.au "Documents/Project" "Documents/Shared"
    python acl_demo.py remove "Documents/Project" amanuensis@weiwu.au "MyOneDrive"
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

def get_item_id(item_path: str, access_token: str) -> Optional[str]:
    """
    Get the item ID for a given path.
    
    Args:
        item_path: Path to the folder or file in OneDrive
        access_token: OAuth access token
        
    Returns:
        Item ID if successful, None otherwise
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{item_path}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Failed to get item info: {resp.status_code}")
            print(f"Response: {resp.text}")
            return None
        
        item_data = resp.json()
        item_id = item_data.get('id')
        if not item_id:
            print("❌ No item ID found in response")
            return None
        
        item_name = item_data.get('name', 'Unknown')
        item_type = 'folder' if 'folder' in item_data else 'file'
        print(f"✅ Found {item_type}: {item_name} (ID: {item_id})")
        return item_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

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
    
    # Get item ID
    item_id = get_item_id(item_path, access_token)
    if not item_id:
        return
    
    # Get permissions for this item
    headers = {"Authorization": f"Bearer {access_token}"}
    permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
    print(f"\nGetting ACL from: {permissions_url}")
    
    try:
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

def invite_permission_to_folders(email: str, folder_paths: List[str], rclone_remote: str = "OneDrive") -> None:
    """
    Send invitation with editing permission for a specific email address to multiple folders (Personal OneDrive).
    
    Args:
        email: Email address to send invitation to
        folder_paths: List of folder paths in OneDrive to grant access to
        rclone_remote: Name of the OneDrive remote in rclone.conf
    """
    print(f"=== OneDrive ACL Manager - Send Invitation to Multiple Folders (Personal OneDrive) ===")
    print(f"Email: {email}")
    print(f"Folders: {', '.join(folder_paths)}")
    print(f"Remote: {rclone_remote}")
    print()
    
    # Get access token
    access_token = get_access_token(rclone_remote)
    if not access_token:
        return
    
    print("✅ Successfully extracted access token from rclone.conf")
    
    # Process each folder
    successful_invites = 0
    failed_invites = 0
    
    for i, folder_path in enumerate(folder_paths, 1):
        print(f"\n--- Processing folder {i}/{len(folder_paths)}: {folder_path} ---")
        
        # Get item ID
        item_id = get_item_id(folder_path, access_token)
        if not item_id:
            print(f"❌ Skipping folder {folder_path} - could not get item ID")
            failed_invites += 1
            continue
        
        # Send invitation (Personal OneDrive)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Send invitation via the invite endpoint (Personal OneDrive)
        invite_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/invite"
        print(f"Sending invitation via: {invite_url}")
        
        invite_data = {
            "requireSignIn": True,
            "roles": ["write"],
            "recipients": [
                {
                    "email": email
                }
            ],
            "message": "You have been granted editing access to this item."
        }
        
        try:
            resp = requests.post(invite_url, headers=headers, json=invite_data, timeout=30)
            print(f"Response Status: {resp.status_code}")
            
            if resp.status_code == 200:
                invite_response = resp.json()
                print("✅ Successfully sent invitation for editing permission!")
                
                # Show invitation details
                value = invite_response.get('value', [])
                if value:
                    for invite in value:
                        print(f"Invitation sent to: {invite.get('grantedTo', {}).get('user', {}).get('email', 'N/A')}")
                        print(f"Roles: {', '.join(invite.get('roles', []))}")
                        if invite.get('invitation'):
                            print(f"Invitation URL: {invite['invitation'].get('inviteUrl', 'N/A')}")
                successful_invites += 1
                
            elif resp.status_code == 201:
                permission = resp.json()
                print("✅ Successfully added editing permission!")
                print(f"Permission ID: {permission.get('id', 'N/A')}")
                print(f"Roles: {', '.join(permission.get('roles', []))}")
                
                # Show granted user info
                granted_to = permission.get('grantedTo')
                if granted_to and granted_to.get('user'):
                    user = granted_to['user']
                    print(f"Granted to: {user.get('displayName', 'N/A')} ({user.get('email', 'N/A')})")
                successful_invites += 1
                
            elif resp.status_code == 400:
                print("❌ Bad request - check the email address format")
                print(f"Response: {resp.text}")
                failed_invites += 1
                
            elif resp.status_code == 403:
                print("❌ Access denied - you may not have permission to modify ACL for this item")
                failed_invites += 1
                
            elif resp.status_code == 404:
                print("❌ User not found - the email address may not exist in your organisation")
                failed_invites += 1
                
            else:
                print(f"❌ Failed to add permission: {resp.status_code}")
                print(f"Response: {resp.text}")
                failed_invites += 1
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            failed_invites += 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            failed_invites += 1
    
    # Summary
    print(f"\n=== Invitation Summary ===")
    print(f"Total folders processed: {len(folder_paths)}")
    print(f"Successful invitations: {successful_invites}")
    print(f"Failed invitations: {failed_invites}")
    
    if successful_invites > 0:
        print(f"✅ Successfully invited {email} to {successful_invites} folder(s)")
    if failed_invites > 0:
        print(f"❌ Failed to invite {email} to {failed_invites} folder(s)")

def remove_permission(item_path: str, email: str, rclone_remote: str = "OneDrive") -> None:
    """
    Remove all permissions for a specific email address.
    
    Args:
        item_path: Path to the folder or file in OneDrive
        email: Email address to remove permissions for
        rclone_remote: Name of the OneDrive remote in rclone.conf
    """
    print(f"=== OneDrive ACL Manager - Remove Permission ===")
    print(f"Item: {item_path}")
    print(f"Email: {email}")
    print(f"Remote: {rclone_remote}")
    print()
    
    # Get access token
    access_token = get_access_token(rclone_remote)
    if not access_token:
        return
    
    print("✅ Successfully extracted access token from rclone.conf")
    
    # Get item ID
    item_id = get_item_id(item_path, access_token)
    if not item_id:
        return
    
    # First, get all permissions to find the one for this email
    headers = {"Authorization": f"Bearer {access_token}"}
    permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
    
    try:
        resp = requests.get(permissions_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Failed to get permissions: {resp.status_code}")
            print(f"Response: {resp.text}")
            return
        
        permissions_data = resp.json()
        permissions = permissions_data.get("value", [])
        
        # Find permission for the specified email
        target_permission_id = None
        for perm in permissions:
            # Check grantedToIdentities (OneDrive Business)
            granted_to_identities = perm.get('grantedToIdentities', [])
            for identity in granted_to_identities:
                if identity.get('user') and identity['user'].get('email') == email:
                    target_permission_id = perm.get('id')
                    break
            
            # Check grantedTo (OneDrive Personal)
            if not target_permission_id:
                granted_to = perm.get('grantedTo')
                if granted_to and granted_to.get('user') and granted_to['user'].get('email') == email:
                    target_permission_id = perm.get('id')
                    break
        
        if not target_permission_id:
            print(f"❌ No permission found for email: {email}")
            return
        
        print(f"✅ Found permission ID: {target_permission_id}")
        
        # Remove the permission
        delete_url = f"{permissions_url}/{target_permission_id}"
        print(f"\nRemoving permission via: {delete_url}")
        
        resp = requests.delete(delete_url, headers=headers, timeout=30)
        print(f"Response Status: {resp.status_code}")
        
        if resp.status_code == 204:
            print("✅ Successfully removed all permissions!")
        elif resp.status_code == 403:
            print("❌ Access denied - you may not have permission to modify ACL for this item")
        elif resp.status_code == 404:
            print("❌ Permission not found - it may have already been removed")
        else:
            print(f"❌ Failed to remove permission: {resp.status_code}")
            print(f"Response: {resp.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Manage ACL for OneDrive items using rclone.conf token")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List ACL for the specified item')
    list_parser.add_argument("item_path", help="Path to the folder or file in OneDrive")
    list_parser.add_argument("remote", nargs="?", default="OneDrive", help="Name of the OneDrive remote (default: OneDrive)")
    
    # Invite command
    invite_parser = subparsers.add_parser('invite', help='Send invitation with editing permission to multiple folders (Personal OneDrive)')
    invite_parser.add_argument("email", help="Email address to send invitation to")
    invite_parser.add_argument("folder_paths", nargs="+", help="One or more folder paths in OneDrive to grant access to")
    invite_parser.add_argument("remote", nargs="?", default="OneDrive", help="Name of the OneDrive remote (default: OneDrive)")
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove all permissions for the email')
    remove_parser.add_argument("item_path", help="Path to the folder or file in OneDrive")
    remove_parser.add_argument("email", help="Email address to remove permissions for")
    remove_parser.add_argument("remote", nargs="?", default="OneDrive", help="Name of the OneDrive remote (default: OneDrive)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("OneDrive ACL Manager")
    print("=" * 50)
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ requests library not found")
        print("Please install it: pip install requests")
        return
    
    # Execute the appropriate command
    if args.command == 'list':
        list_item_acl(args.item_path, args.remote)
    elif args.command == 'invite':
        invite_permission_to_folders(args.email, args.folder_paths, args.remote)
    elif args.command == 'remove':
        remove_permission(args.item_path, args.email, args.remote)
    
    print("\n=== ACL Management Complete ===")
    print("This demonstrates direct access to OneDrive ACL via Microsoft Graph API")
    print("using the OAuth token from rclone.conf.")

if __name__ == "__main__":
    main()
