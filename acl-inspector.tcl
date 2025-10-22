#!/usr/bin/env tclsh
#
# OneDrive ACL Lister - Tcl/Tk GUI Version with Command Line Support
# Using rclone.conf token to access Microsoft Graph API directly
#
# This script demonstrates how to:
# 1. Read the OAuth token from rclone.conf
# 2. Use it to make direct Microsoft Graph API calls
# 3. Display ACL (Access Control List) in a treeview widget or console
#
# Prerequisites:
# - rclone must be installed and configured with OneDrive remote
# - tls package for HTTPS requests (package require tls)
# - Valid OAuth token in ~/.config/rclone/rclone.conf
#
# Usage:
#    GUI mode:    wish acl_demo.tcl [item_path] [remote_name]
#    CLI mode:    tclsh acl_demo.tcl <item_path> [remote_name]
#    
#    item_path: Required. Path to the folder or file in OneDrive
#    remote_name: Optional. Name of the OneDrive remote (default: OneDrive)
#
# Example:
#    wish acl_demo.tcl "Documents"
#    tclsh acl_demo.tcl "Documents/Project" "MyOneDrive"

# Check if we're running in GUI mode (wish) or CLI mode (tclsh)
set gui_mode [expr {[info commands tk] ne ""}]

if {$gui_mode} {
    package require Tk
    package require Ttk
}

package require http
package require json
package require tls

# Configure TLS for HTTPS requests
::http::register https 443 [list ::tls::socket]

# Global variables
set access_token ""
set item_path ""
set remote_name "OneDrive"

if {$gui_mode} {
    # Create main window
    wm title . "OneDrive ACL Lister"
    wm geometry . "800x600"
    wm minsize . 600 400

    # Create main frame
    set main_frame [frame .main]
    pack $main_frame -fill both -expand yes -padx 10 -pady 10

    # Create input frame
    set input_frame [frame $main_frame.input]
    pack $input_frame -fill x -pady {0 10}

    # Item path input
    set path_frame [frame $input_frame.path]
    pack $path_frame -fill x -pady 2
    label $path_frame.label -text "OneDrive Item Path:"
    pack $path_frame.label -side left
    set path_entry [entry $path_frame.entry -width 50]
    pack $path_frame.entry -side left -fill x -expand yes -padx {5 0}

    # Remote name input
    set remote_frame [frame $input_frame.remote]
    pack $remote_frame -fill x -pady 2
    label $remote_frame.label -text "Remote Name:"
    pack $remote_frame.label -side left
    set remote_entry [entry $remote_frame.entry -width 20]
    pack $remote_entry -side left -fill x -expand yes -padx {5 0}
    $remote_entry insert 0 "OneDrive"

    # Buttons frame
    set button_frame [frame $input_frame.buttons]
    pack $button_frame -fill x -pady {10 0}

    set fetch_button [button $button_frame.fetch -text "Fetch ACL" -command fetch_acl]
    pack $fetch_button -side left -padx {0 5}

    set clear_button [button $button_frame.clear -text "Clear" -command clear_treeview]
    pack $clear_button -side left

    # Status label
    set status_label [label $main_frame.status -text "Ready" -fg blue]
    pack $status_label -fill x -pady {0 10}

    # Create treeview frame
    set tree_frame [frame $main_frame.tree]
    pack $tree_frame -fill both -expand yes

    # Create treeview with scrollbars
    set tree_container [frame $tree_frame.container]
    pack $tree_container -fill both -expand yes

    # Treeview widget
    set tree [ttk::treeview $tree_container.tree -columns {id roles user email link_type link_scope expires} -show {tree headings}]
    pack $tree -side left -fill both -expand yes

    # Scrollbars
    set v_scrollbar [scrollbar $tree_container.vscroll -orient vertical -command "$tree yview"]
    pack $v_scrollbar -side right -fill y
    $tree configure -yscrollcommand "$v_scrollbar set"

    set h_scrollbar [scrollbar $tree_frame.hscroll -orient horizontal -command "$tree xview"]
    pack $h_scrollbar -fill x
    $tree configure -xscrollcommand "$h_scrollbar set"

    # Configure treeview columns
    $tree heading #0 -text "Permission"
    $tree column #0 -width 100 -minwidth 80

    $tree heading id -text "ID"
    $tree column id -width 200 -minwidth 150

    $tree heading roles -text "Roles"
    $tree column roles -width 80 -minwidth 60

    $tree heading user -text "User"
    $tree column user -width 150 -minwidth 100

    $tree heading email -text "Email"
    $tree column email -width 200 -minwidth 150

    $tree heading link_type -text "Link Type"
    $tree column link_type -width 80 -minwidth 60

    $tree heading link_scope -text "Link Scope"
    $tree column link_scope -width 80 -minwidth 60

    $tree heading expires -text "Expires"
    $tree column expires -width 120 -minwidth 100

    # Configure tags for different permission types
    $tree tag configure owner -background lightgreen
    $tree tag configure write -background lightblue
    $tree tag configure read -background lightyellow
}

proc update_status {message {color blue}} {
    global status_label gui_mode
    if {$gui_mode} {
        $status_label configure -text $message -fg $color
    } else {
        puts "STATUS: $message"
    }
}

proc clear_treeview {} {
    global tree gui_mode
    if {$gui_mode} {
        foreach item [$tree children {}] {
            $tree delete $item
        }
        update_status "Treeview cleared" green
    }
}

proc display_acl_cli {permissions item_id} {
    set perm_count [llength $permissions]
    puts "\n=== ACL Information ==="
    puts "Folder ID: $item_id"
    puts "Found $perm_count permission(s):"
    puts ""
    
    # Print table header
    puts [format "%-4s %-15s %-25s %-30s" "No." "Role" "User" "Email"]
    puts [string repeat "-" 80]
    
    set perm_num 1
    foreach perm $permissions {
        set roles [dict get $perm roles]
        set roles_str [join $roles ", "]
        
        # Get user information
        set user_name "N/A"
        set user_email "N/A"
        
        if {[dict exists $perm grantedTo user]} {
            set user [dict get $perm grantedTo user]
            set user_name [dict get $user displayName]
            set user_email [dict get $user email]
        } elseif {[dict exists $perm grantedToIdentities]} {
            set identities [dict get $perm grantedToIdentities]
            if {[llength $identities] > 0} {
                set identity [lindex $identities 0]
                if {[dict exists $identity user]} {
                    set user [dict get $identity user]
                    set user_name [dict get $user displayName]
                    set user_email [dict get $user email]
                }
            }
        }
        
        # Truncate long names/emails for table format
        if {[string length $user_name] > 24} {
            set user_name "[string range $user_name 0 21]..."
        }
        if {[string length $user_email] > 29} {
            set user_email "[string range $user_email 0 26]..."
        }
        
        puts [format "%-4d %-15s %-25s %-30s" $perm_num $roles_str $user_name $user_email]
        
        incr perm_num
    }
    puts ""
}

proc get_access_token {rclone_remote} {
    set conf_path [file join ~ .config rclone rclone.conf]
    
    if {![file exists $conf_path]} {
        update_status "Error: rclone config not found at $conf_path" red
        return ""
    }
    
    # Read config file
    set config_data [read [open $conf_path r]]
    
    # Find the remote section
    set remote_section ""
    set in_remote_section 0
    
    foreach line [split $config_data \n] {
        if {[string match "\\\[$rclone_remote\\\]" [string trim $line]]} {
            set in_remote_section 1
            continue
        }
        
        if {$in_remote_section} {
            if {[string match "\\\[*\\\]" [string trim $line]]} {
                break
            }
            if {[string match "token*" [string trim $line]]} {
                set token_line [string trim $line]
                set token_json [string range $token_line 6 end]
                break
            }
        }
    }
    
    if {![info exists token_json]} {
        update_status "Error: No token found for remote '$rclone_remote'" red
        return ""
    }
    
    # Parse JSON token
    if {[catch {json::json2dict $token_json} token_dict]} {
        update_status "Error: Could not parse token JSON: $token_dict" red
        return ""
    }
    
    set access_token [dict get $token_dict access_token]
    if {$access_token eq ""} {
        update_status "Error: No access_token in token JSON" red
        return ""
    }
    
    return $access_token
}

proc make_http_request {url headers} {
    set token [dict get $headers Authorization]
    
    if {[catch {
        set response [http::geturl $url -headers [list Authorization $token] -timeout 30000]
        set status [http::ncode $response]
        set data [http::data $response]
        http::cleanup $response
        set result [list $status $data]
    } error]} {
        set result [list "error" $error]
    }
    return $result
}

proc fetch_acl {{item_path ""} {remote_name "OneDrive"}} {
    global path_entry remote_entry tree gui_mode
    
    if {$gui_mode} {
        set item_path [$path_entry get]
        set remote_name [$remote_entry get]
    }
    
    if {$item_path eq ""} {
        update_status "Error: Please enter an item path" red
        return
    }
    
    update_status "Fetching ACL for: $item_path" blue
    
    # Clear existing treeview
    clear_treeview
    
    # Get access token
    set access_token [get_access_token $remote_name]
    if {$access_token eq ""} {
        return
    }
    
    update_status "✅ Successfully extracted access token from rclone.conf" green
    
    # Get item info - URL encode the path
    set encoded_path [string map {" " "%20" "✈️" "%E2%9C%88%EF%B8%8F"} $item_path]
    set item_url "https://graph.microsoft.com/v1.0/me/drive/root:/$encoded_path"
    update_status "Getting item info from: $item_url" blue
    
    set result [make_http_request $item_url [list Authorization "Bearer $access_token"]]
    set status [lindex $result 0]
    set data [lindex $result 1]
    
    if {$status ne "200"} {
        if {$status eq "error"} {
            update_status "❌ HTTP request failed: $data" red
        } else {
            update_status "❌ Failed to get item info: $status - $data" red
        }
        return
    }
    
    # Parse item response
    if {[catch {json::json2dict $data} item_dict]} {
        update_status "❌ Failed to parse item response: $item_dict" red
        return
    }
    
    set item_id [dict get $item_dict id]
    set item_name [dict get $item_dict name]
    set item_type [expr {[dict exists $item_dict folder] ? "folder" : "file"}]
    
    update_status "✅ Found $item_type: $item_name (ID: $item_id)" green
    
    # Get permissions
    set permissions_url "https://graph.microsoft.com/v1.0/me/drive/items/$item_id/permissions"
    update_status "Getting ACL from: $permissions_url" blue
    
    set result [make_http_request $permissions_url [list Authorization "Bearer $access_token"]]
    set status [lindex $result 0]
    set data [lindex $result 1]
    
    if {$status ne "200"} {
        if {$status eq "403"} {
            update_status "❌ Access denied - you may not have permission to view ACL for this item" red
        } else {
            update_status "❌ Failed to get ACL: $status" red
        }
        return
    }
    
    # Parse permissions response
    if {[catch {json::json2dict $data} permissions_dict]} {
        update_status "❌ Failed to parse permissions response: $permissions_dict" red
        return
    }
    
    set permissions [dict get $permissions_dict value]
    set perm_count [llength $permissions]
    
    if {$perm_count == 0} {
        update_status "ℹ️ No permissions found for this item (empty ACL)" orange
        return
    }
    
    update_status "✅ Found $perm_count permission(s) in ACL" green
    
    if {$gui_mode} {
        # Populate treeview
        set perm_num 1
        foreach perm $permissions {
            set perm_id [dict get $perm id]
            set roles [dict get $perm roles]
            set roles_str [join $roles ", "]
            
            # Get user information
            set user_name "N/A"
            set user_email "N/A"
            
            if {[dict exists $perm grantedTo user]} {
                set user [dict get $perm grantedTo user]
                set user_name [dict get $user displayName]
                set user_email [dict get $user email]
            } elseif {[dict exists $perm grantedToIdentities]} {
                set identities [dict get $perm grantedToIdentities]
                if {[llength $identities] > 0} {
                    set identity [lindex $identities 0]
                    if {[dict exists $identity user]} {
                        set user [dict get $identity user]
                        set user_name [dict get $user displayName]
                        set user_email [dict get $user email]
                    }
                }
            }
            
            # Get link information
            set link_type "N/A"
            set link_scope "N/A"
            if {[dict exists $perm link]} {
                set link [dict get $perm link]
                if {[dict exists $link type]} {
                    set link_type [dict get $link type]
                }
                if {[dict exists $link scope]} {
                    set link_scope [dict get $link scope]
                }
            }
            
            # Get expiration
            set expires "N/A"
            if {[dict exists $perm expirationDateTime]} {
                set expires [dict get $perm expirationDateTime]
            }
            
            # Determine tag based on roles
            set tag "write"
            if {[lsearch $roles "owner"] >= 0} {
                set tag "owner"
            } elseif {[lsearch $roles "read"] >= 0} {
                set tag "read"
            }
            
            # Insert into treeview
            $tree insert {} end -text "Permission $perm_num" \
                -values [list $perm_id $roles_str $user_name $user_email $link_type $link_scope $expires] \
                -tags $tag
            
            incr perm_num
        }
    } else {
        # Display in CLI mode
        display_acl_cli $permissions $item_id
    }
    
    update_status "✅ ACL listing complete - $perm_count permission(s) displayed" green
}

if {$gui_mode} {
    # GUI mode - create interface
    # Bind Enter key to fetch button
    bind $path_entry <Return> fetch_acl
    bind $remote_entry <Return> fetch_acl
    
    # Set focus to path entry
    focus $path_entry
    
    # Main event loop
    if {[info exists argv] && [llength $argv] > 0} {
        set item_path [lindex $argv 0]
        $path_entry insert 0 $item_path
        
        if {[llength $argv] > 1} {
            set remote_name [lindex $argv 1]
            $remote_entry delete 0 end
            $remote_entry insert 0 $remote_name
        }
    }
    
    update_status "OneDrive ACL Lister - Ready to fetch ACL information" blue
} else {
    # CLI mode - process command line arguments
    if {[info exists argv] && [llength $argv] > 0} {
        set item_path [lindex $argv 0]
        set remote_name "OneDrive"
        
        if {[llength $argv] > 1} {
            set remote_name [lindex $argv 1]
        }
        
        puts "OneDrive ACL Lister - CLI Mode"
        puts "Item Path: $item_path"
        puts "Remote Name: $remote_name"
        puts ""
        
        # Fetch ACL
        fetch_acl $item_path $remote_name
    } else {
        puts "Usage: tclsh acl_demo.tcl <item_path> [remote_name]"
        puts "Example: tclsh acl_demo.tcl \"✈️ Tourism Transformation\""
        exit 1
    }
} 