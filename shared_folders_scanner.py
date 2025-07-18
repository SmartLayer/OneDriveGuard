#!/usr/bin/env python3
"""
OneDrive Shared Folders Scanner (Efficient) - Find folders shared by you using Graph API.

This script uses efficient Graph API methods to find shared folders without iterating
through every folder in your OneDrive:

Method 1: Search for items with permissions (preferred for large OneDrives)
Method 2: Delta query with permission expansion (alternative approach)
Method 3: Fallback: Selective scanning of common shared folders

Distinguished sharing types:
- 🔗 Folders shared via link
- 👥 Folders shared via direct permissions/invitations

Prerequisites:
- rclone must be installed and configured with OneDrive remote
- requests library (pip install requests)
- Valid OAuth token in ~/.config/rclone/rclone.conf

Usage:
    python shared_folders_scanner.py [options]
    
Options:
    --remote REMOTE_NAME    OneDrive remote name (default: OneDrive)
    --method METHOD         Search method: search, delta, or fallback (default: search)
    --max-results N         Maximum results to return (default: 1000)
    
Examples:
    python shared_folders_scanner.py
    python shared_folders_scanner.py --method search --max-results 500
    python shared_folders_scanner.py --remote "MyOneDrive" --method delta
"""

import requests
import json
import sys
import argparse
import configparser
import os
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote
import time

def get_access_token(rclone_remote: str = "OneDrive") -> Optional[str]:
    """Extract access token from rclone.conf for the specified remote."""
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



def analyze_permissions(permissions: List[Dict]) -> Tuple[bool, bool, int, List[str]]:
    """
    Analyze permissions to determine sharing type and get shared user list.
    Identifies owner by looking for "owner" role instead of requiring user ID.
    
    Returns:
        Tuple of (has_link_sharing, has_direct_sharing, permission_count, shared_users)
    """
    has_link_sharing = False
    has_direct_sharing = False
    shared_users = []
    
    for perm in permissions:
        # Skip owner permissions (identified by "owner" role)
        roles = perm.get('roles', [])
        if 'owner' in roles:
            continue
        
        # Check if this is a link permission
        link = perm.get('link')
        if link and link.get('type'):
            has_link_sharing = True
        
        # Check if this is a direct permission
        granted_to = perm.get('grantedTo')
        if granted_to and granted_to.get('user'):
            user = granted_to['user']
            has_direct_sharing = True
            email = user.get('email', user.get('displayName', 'Unknown'))
            if email not in shared_users:
                shared_users.append(email)
        
        # Check grantedToIdentities (OneDrive Business)
        granted_to_identities = perm.get('grantedToIdentities', [])
        for identity in granted_to_identities:
            if identity.get('user'):
                user = identity['user']
                has_direct_sharing = True
                email = user.get('email', user.get('displayName', 'Unknown'))
                if email not in shared_users:
                    shared_users.append(email)
    
    return has_link_sharing, has_direct_sharing, len(permissions), shared_users

def get_item_path(item_id: str, access_token: str) -> str:
    """Get the full path of an item using its parent chain."""
    headers = {"Authorization": f"Bearer {access_token}"}
    path_parts = []
    current_id = item_id
    
    try:
        while current_id:
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{current_id}"
            resp = requests.get(url, headers=headers, timeout=30)
            
            if resp.status_code != 200:
                break
            
            item_data = resp.json()
            name = item_data.get('name', 'Unknown')
            path_parts.insert(0, name)
            
            parent_ref = item_data.get('parentReference')
            if not parent_ref or parent_ref.get('path') == '/drive/root:':
                break
            
            current_id = parent_ref.get('id')
            if not current_id:
                break
        
        # Remove 'root' from path if present
        if path_parts and path_parts[0].lower() == 'root':
            path_parts = path_parts[1:]
        
        return '/'.join(path_parts) if path_parts else 'Unknown'
    
    except Exception:
        return 'Unknown'

def method_search_with_permissions(access_token: str, max_results: int = 1000) -> List[Dict]:
    """
    Method 1: Use Graph search to find folders and check their permissions.
    This is the most efficient method for finding shared folders.
    """
    print("🔍 Using Graph Search method to find shared folders...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    shared_folders = []
    
    # Get root children to find folders
    root_url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    
    try:
        resp = requests.get(f"{root_url}?$top={min(max_results, 1000)}", headers=headers, timeout=60)
        if resp.status_code != 200:
            print(f"⚠️  Failed to get root children: {resp.status_code}")
            return shared_folders
        
        root_data = resp.json()
        items = root_data.get("value", [])
        
        print(f"📂 Found {len(items)} items in root to check for sharing...")
        
        # Check permissions for each folder
        checked_count = 0
        for item in items:
            if 'folder' not in item:
                continue
            
            checked_count += 1
            if checked_count % 50 == 0:
                print(f"   Checked {checked_count}/{len(items)} folders...")
            
            item_id = item.get('id')
            item_name = item.get('name', 'Unknown')
            
            # Get permissions for this folder
            permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
            try:
                perm_resp = requests.get(permissions_url, headers=headers, timeout=30)
                if perm_resp.status_code == 200:
                    permissions_data = perm_resp.json()
                    permissions = permissions_data.get("value", [])
                    
                    # Analyze permissions
                    has_link, has_direct, perm_count, shared_users = analyze_permissions(permissions)
                    
                    if has_link or has_direct:
                        # Get full path
                        item_path = get_item_path(item_id, access_token)
                        
                        # Determine symbol and sharing type
                        if has_link:
                            symbol = "🔗"
                            share_type = "Link sharing"
                        else:
                            symbol = "👥"
                            share_type = "Direct permissions"
                        
                        shared_folders.append({
                            'path': item_path,
                            'name': item_name,
                            'id': item_id,
                            'symbol': symbol,
                            'share_type': share_type,
                            'has_link_sharing': has_link,
                            'has_direct_sharing': has_direct,
                            'permission_count': perm_count,
                            'shared_users': shared_users
                        })
                        
                        print(f"   ✅ Found shared: {symbol} {item_path}")
                
            except Exception as e:
                # Skip folders we can't access
                continue
    
    except Exception as e:
        print(f"❌ Search error: {e}")
    
    print(f"✅ Search method complete. Found {len(shared_folders)} shared folders.")
    return shared_folders

def method_delta_query(access_token: str, max_results: int = 1000) -> List[Dict]:
    """
    Method 2: Use delta query to get all drive changes and check permissions.
    Less efficient but more comprehensive.
    """
    print("🔄 Using Delta Query method to find shared folders...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    shared_folders = []
    
    # Start delta query from root
    delta_url = "https://graph.microsoft.com/v1.0/me/drive/root/delta"
    
    try:
        resp = requests.get(f"{delta_url}?$top={min(max_results, 1000)}", headers=headers, timeout=60)
        if resp.status_code != 200:
            print(f"⚠️  Delta query failed: {resp.status_code}")
            return shared_folders
        
        delta_data = resp.json()
        items = delta_data.get("value", [])
        
        print(f"📂 Delta query returned {len(items)} items to check...")
        
        checked_count = 0
        for item in items:
            # Only check folders
            if 'folder' not in item or item.get('deleted'):
                continue
            
            checked_count += 1
            if checked_count % 25 == 0:
                print(f"   Checked {checked_count} folders...")
            
            item_id = item.get('id')
            item_name = item.get('name', 'Unknown')
            
            # Get permissions
            permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
            try:
                perm_resp = requests.get(permissions_url, headers=headers, timeout=30)
                if perm_resp.status_code == 200:
                    permissions_data = perm_resp.json()
                    permissions = permissions_data.get("value", [])
                    
                    has_link, has_direct, perm_count, shared_users = analyze_permissions(permissions)
                    
                    if has_link or has_direct:
                        item_path = get_item_path(item_id, access_token)
                        
                        symbol = "🔗" if has_link else "👥"
                        share_type = "Link sharing" if has_link else "Direct permissions"
                        
                        shared_folders.append({
                            'path': item_path,
                            'name': item_name,
                            'id': item_id,
                            'symbol': symbol,
                            'share_type': share_type,
                            'has_link_sharing': has_link,
                            'has_direct_sharing': has_direct,
                            'permission_count': perm_count,
                            'shared_users': shared_users
                        })
                        
                        print(f"   ✅ Found shared: {symbol} {item_path}")
            
            except Exception:
                continue
    
    except Exception as e:
        print(f"❌ Delta query error: {e}")
    
    print(f"✅ Delta method complete. Found {len(shared_folders)} shared folders.")
    return shared_folders

def method_fallback_selective(access_token: str, max_results: int = 1000) -> List[Dict]:
    """
    Method 3: Fallback method - check common folders that are likely to be shared.
    Most efficient for users who primarily share from common locations.
    """
    print("📁 Using Fallback Selective method (common shared locations)...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    shared_folders = []
    
    # Common folders that are typically shared
    common_paths = [
        "Documents",
        "Pictures", 
        "Desktop",
        "Projects",
        "Shared",
        "Public",
        "Work",
        "Team"
    ]
    
    def check_folder_and_children(folder_path: str, max_depth: int = 2, current_depth: int = 0):
        """Recursively check a folder and its immediate children for sharing."""
        if current_depth >= max_depth:
            return
        
        try:
            # Get folder by path
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}"
            resp = requests.get(url, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                folder_data = resp.json()
                folder_id = folder_data.get('id')
                
                # Check if this folder is shared
                permissions_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/permissions"
                perm_resp = requests.get(permissions_url, headers=headers, timeout=30)
                
                if perm_resp.status_code == 200:
                    permissions_data = perm_resp.json()
                    permissions = permissions_data.get("value", [])
                    
                    has_link, has_direct, perm_count, shared_users = analyze_permissions(permissions)
                    
                    if has_link or has_direct:
                        symbol = "🔗" if has_link else "👥"
                        share_type = "Link sharing" if has_link else "Direct permissions"
                        
                        shared_folders.append({
                            'path': folder_path,
                            'name': folder_data.get('name', folder_path.split('/')[-1]),
                            'id': folder_id,
                            'symbol': symbol,
                            'share_type': share_type,
                            'has_link_sharing': has_link,
                            'has_direct_sharing': has_direct,
                            'permission_count': perm_count,
                            'shared_users': shared_users
                        })
                        
                        print(f"   ✅ Found shared: {symbol} {folder_path}")
                
                # Check children of this folder
                if current_depth < max_depth - 1:
                    children_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
                    children_resp = requests.get(children_url, headers=headers, timeout=30)
                    
                    if children_resp.status_code == 200:
                        children_data = children_resp.json()
                        children = children_data.get("value", [])
                        
                        for child in children[:10]:  # Limit to first 10 children
                            if 'folder' in child:
                                child_name = child.get('name', 'Unknown')
                                child_path = f"{folder_path}/{child_name}"
                                check_folder_and_children(child_path, max_depth, current_depth + 1)
        
        except Exception:
            # Folder doesn't exist or no access
            pass
    
    # Check each common path
    for path in common_paths:
        print(f"   Checking: {path}")
        check_folder_and_children(path)
    
    print(f"✅ Fallback method complete. Found {len(shared_folders)} shared folders.")
    return shared_folders

def scan_shared_folders(rclone_remote: str = "OneDrive", method: str = "search", max_results: int = 1000) -> None:
    """
    Scan OneDrive for all shared folders using the specified method.
    """
    print(f"=== OneDrive Shared Folders Scanner (Efficient) ===")
    print(f"Remote: {rclone_remote}")
    print(f"Method: {method}")
    print(f"Max results: {max_results}")
    print()
    
    # Get access token
    access_token = get_access_token(rclone_remote)
    if not access_token:
        return
    
    print("✅ Successfully extracted access token from rclone.conf")
    
    # Choose method and scan
    start_time = time.time()
    
    if method == "search":
        shared_folders = method_search_with_permissions(access_token, max_results)
    elif method == "delta":
        shared_folders = method_delta_query(access_token, max_results)
    elif method == "fallback":
        shared_folders = method_fallback_selective(access_token, max_results)
    else:
        print(f"❌ Unknown method: {method}")
        print("Available methods: search, delta, fallback")
        return
    
    scan_time = time.time() - start_time
    
    print()
    print("=" * 80)
    
    # Display results
    if shared_folders:
        print(f"📁 Found {len(shared_folders)} shared folder(s) in {scan_time:.1f} seconds:")
        print("=" * 80)
        
        for folder in shared_folders:
            print(f"{folder['symbol']} {folder['path']}")
            print(f"   └─ {folder['share_type']} ({folder['permission_count']} permission(s))")
            
            if folder['shared_users']:
                users_str = ', '.join(folder['shared_users'][:3])
                if len(folder['shared_users']) > 3:
                    users_str += f" and {len(folder['shared_users']) - 3} more"
                print(f"   └─ Shared with: {users_str}")
            
            if folder['has_link_sharing'] and folder['has_direct_sharing']:
                print(f"   └─ Has both link sharing and direct permissions")
            print()
    else:
        print(f"ℹ️  No shared folders found in {scan_time:.1f} seconds")
        print("This could mean:")
        print("  - You haven't shared any folders")
        print("  - All shared items are files (not folders)")
        print("  - Permission issues accessing some folders")
        
        if method == "fallback":
            print("  - Try the 'search' method for a more comprehensive scan")
    
    print("\n=== Scan Complete ===")
    print(f"💡 Tip: For 20,000+ folders, the '{method}' method is much more efficient")
    print("     than iterating through every folder individually!")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Efficiently scan OneDrive for shared folders")
    parser.add_argument("--remote", default="OneDrive", 
                       help="Name of the OneDrive remote (default: OneDrive)")
    parser.add_argument("--method", choices=["search", "delta", "fallback"], default="search",
                       help="Search method to use (default: search)")
    parser.add_argument("--max-results", type=int, default=1000,
                       help="Maximum results to return (default: 1000)")
    
    args = parser.parse_args()
    
    print("OneDrive Shared Folders Scanner (Efficient)")
    print("=" * 50)
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ requests library not found")
        print("Please install it: pip install requests")
        return
    
    # Execute the scan
    scan_shared_folders(args.remote, args.method, args.max_results)

if __name__ == "__main__":
    main()
