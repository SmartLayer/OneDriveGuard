# OneDrive ACL Manager

This project provides comprehensive tools for managing Access Control Lists (ACLs) in OneDrive using the Microsoft Graph API with OAuth tokens from rclone configuration.

## Features

- **ACL Management**: List, invite, and remove permissions for OneDrive items
- **ACL Scanning**: Find all folders with ACL permissions across your OneDrive
- **Direct API Access**: Uses OAuth tokens from rclone.conf to access Microsoft Graph API directly
- **Cross-Platform**: Supports both OneDrive Personal and OneDrive Business accounts
- **Multiple Interfaces**: Python command-line tools and Tcl/Tk GUI

## Project Structure

```
onedrive-acl/
├── src/                    # Python source code
│   ├── __init__.py        # Package initialisation
│   ├── acl_manager.py     # Main ACL management tool
│   ├── acl_scanner.py     # ACL scanning and discovery
│   ├── config_utils.py    # Shared configuration utilities
│   └── debug_permissions.py # Debug tools for permission analysis
├── acl_demo.tcl           # Tcl/Tk GUI version
└── README.md              # This file
```

## Prerequisites

### For Python Version
- Python 3.6+
- rclone installed and configured with OneDrive remote
- `requests` library: `pip install requests`
- Valid OAuth token in `~/.config/rclone/rclone.conf`. Assuming that the relevant section in rclone.conf goes by the name `OneDrive-ACL`, you can get one by

   $ rclone config update OneDrive-ACL --onedrive-metadata-permissions write

### For Tcl/Tk Version
- Tcl/Tk 8.6+
- rclone installed and configured with OneDrive remote
- `tls` package for HTTPS requests
- `json` package for JSON parsing
- Valid OAuth token in `~/.config/rclone/rclone.conf`

## Installation

1. **Install rclone** (if not already installed):
   ```bash
   # Download and install rclone from https://rclone.org/downloads/
   ```

2. **Configure rclone with OneDrive**:
   ```bash
   rclone config
   # Follow the prompts to add a OneDrive remote
   ```

3. **Authenticate with OneDrive**:
   ```bash
   rclone authorize onedrive
   ```

4. **Install Python dependencies** (for Python version):
   ```bash
   pip install requests
   ```

5. **Install Tcl packages** (for Tcl/Tk version):
   ```bash
   # On Ubuntu/Debian:
   sudo apt-get install tcllib
   
   # On macOS with Homebrew:
   brew install tcl-tk
   
   # On Windows, these packages are usually included with ActiveTcl
   ```

## Usage

### ACL Manager (Python)

The main ACL management tool provides comprehensive permission control:

```bash
python -m src.acl_manager <command> [options]
```

**Commands:**
- `list <item_path> [remote_name]` - List ACL for the specified item
- `invite <email> <folder_path>... [remote_name]` - Send invitation with editing permission to multiple folders (Personal OneDrive)
- `remove <item_path> <email> [remote_name]` - Remove all permissions for the email

**Examples:**
```bash
# List ACL for a folder
python -m src.acl_manager list "Documents"

# List ACL for a specific file
python -m src.acl_manager list "Documents/file.txt"

# Use a different remote name
python -m src.acl_manager list "Project Files" "MyOneDrive"

# Invite a user to multiple folders
python -m src.acl_manager invite amanuensis@weiwu.au "Documents/Project" "Documents/Shared"

# Remove user permissions
python -m src.acl_manager remove "Documents/Project" amanuensis@weiwu.au "MyOneDrive"
```

### ACL Scanner (Python)

Scan your OneDrive for folders with ACL permissions:

```bash
python -m src.acl_scanner [options] [dirname]
```

**Options:**
- `--remote REMOTE_NAME` - OneDrive remote name (default: OneDrive)
- `--max-results N` - Maximum results to return (default: 1000)
- `--only-user EMAIL` - Filter to show only folders shared with specific user
- `dirname` - Optional: scan only under this directory path

**Examples:**
```bash
# Scan all folders for ACL permissions
python -m src.acl_scanner

# Scan specific directory
python -m src.acl_scanner "Documents/Projects"

# Filter by user
python -m src.acl_scanner --only-user "user@example.com"

# Combine filters
python -m src.acl_scanner --only-user "user@example.com" "Work"

# Limit results
python -m src.acl_scanner --max-results 500

# Use different remote
python -m src.acl_scanner --remote "MyOneDrive"
```

### Tcl/Tk GUI Version

The Tcl/Tk version provides a graphical interface:

```bash
tclsh acl_demo.tcl <item_path> [remote_name]
```

**Examples:**
```bash
# List ACL for a folder with GUI
tclsh acl_demo.tcl "Documents"

# List ACL for a specific file with GUI
tclsh acl_demo.tcl "Documents/file.txt"

# Use a different remote name
tclsh acl_demo.tcl "Project Files" "MyOneDrive"
```

## GUI Features (Tcl/Tk Version)

The Tcl/Tk version provides a graphical interface with:

- **Input fields** for OneDrive item path and remote name
- **Treeview widget** displaying ACL information in columns:
  - Permission number
  - ID
  - Roles (owner, write, read)
  - User name
  - Email address
  - Link type
  - Link scope
  - Expiration date
- **Colour coding** for different permission types:
  - Green: Owner permissions
  - Blue: Write permissions
  - Yellow: Read permissions
- **Status updates** showing progress and error messages
- **Scrollbars** for viewing large ACL lists
- **Clear button** to reset the display

## Output Information

Both versions display the following ACL information:

- **Permission ID**: Unique identifier for each permission
- **Roles**: Access level (owner, write, read)
- **User Information**: Display name and email address
- **Link Details**: Type and scope of sharing links
- **Expiration**: When the permission expires (if applicable)
- **Password Protection**: Whether the shared link requires a password

## Troubleshooting

### Common Issues

1. **"rclone config not found"**
   - Ensure rclone is installed and configured
   - Run `rclone config` to set up your OneDrive remote

2. **"No token found"**
   - Re-authenticate with OneDrive: `rclone authorize onedrive`
   - Check that the remote name matches your configuration

3. **"Access denied"**
   - Verify you have permission to view the ACL for the specified item
   - Check that the item path is correct
   - Ensure your Microsoft Graph API permissions are sufficient

4. **"Network error"**
   - Check your internet connection
   - Verify firewall settings allow HTTPS connections to Microsoft Graph API

### Tcl/Tk Specific Issues

1. **"package require tls" fails**
   - Install the tls package for your Tcl distribution
   - On Ubuntu: `sudo apt-get install tcllib`
   - On macOS: `brew install tcl-tk`

2. **"package require json" fails**
   - Install the json package for your Tcl distribution
   - Usually included with tcllib

## API Details

The scripts use the Microsoft Graph API endpoints:

- **Get Item**: `GET /me/drive/root:/{item-path}`
- **Get Permissions**: `GET /me/drive/items/{item-id}/permissions`
- **Create Permission**: `POST /me/drive/items/{item-id}/invite`
- **Delete Permission**: `DELETE /me/drive/items/{item-id}/permissions/{permission-id}`

The OAuth token is extracted from rclone's configuration file and used directly in API requests, bypassing the need for separate authentication.

## Security Notes

- The OAuth token is read from rclone.conf and used directly
- No credentials are stored by these scripts
- Tokens expire and may need to be refreshed via `rclone authorize onedrive`
- The scripts can read, create, and delete ACL information; use with appropriate caution

## License

This project is provided as-is for educational and demonstration purposes. 
