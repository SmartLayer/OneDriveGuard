#!/bin/bash
# Test OAuth flow using rclone and inspect the token response

echo "================================================================================"
echo "OneDrive OAuth Token Inspection Experiment"
echo "================================================================================"
echo ""
echo "This script will use rclone to get a fresh token and inspect its contents."
echo ""
echo "We'll create a temporary rclone remote configuration and then examine the token."
echo ""

# Create a temporary config name
TEMP_REMOTE="OneDrive-Test-$$"

echo "Creating temporary rclone remote: $TEMP_REMOTE"
echo ""

# Use rclone config create with OneDrive
echo "Running: rclone config create $TEMP_REMOTE onedrive config_is_local false"
echo ""
echo "This will open your browser for authentication..."
echo "Please complete the authentication process."
echo ""

# Create the config (this will trigger OAuth flow)
rclone config create "$TEMP_REMOTE" onedrive \
    config_is_local false \
    config_refresh_token false 2>&1 | tee /tmp/rclone_output.log

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Configuration created successfully!"
    echo ""
    
    # Extract and display the token
    echo "================================================================================"
    echo "📋 Examining token from ~/.config/rclone/rclone.conf"
    echo "================================================================================"
    echo ""
    
    # Extract the token section for our remote
    TOKEN_JSON=$(grep -A 3 "^\[$TEMP_REMOTE\]" ~/.config/rclone/rclone.conf | grep "^token = " | sed 's/^token = //')
    
    if [ -n "$TOKEN_JSON" ]; then
        echo "🔍 Raw token JSON (first 200 chars):"
        echo "$TOKEN_JSON" | cut -c1-200
        echo "..."
        echo ""
        
        echo "📊 Parsed token fields:"
        echo "$TOKEN_JSON" | python3 -c "
import sys
import json

try:
    token = json.load(sys.stdin)
    
    print('Token fields present:')
    for key in token.keys():
        if key == 'access_token':
            print(f'  ✓ {key}: {token[key][:30]}...{token[key][-20:]} (length: {len(token[key])})')
        elif key == 'refresh_token':
            print(f'  ✓ {key}: {token[key][:30]}... (length: {len(token[key])})')
        elif key == 'scope':
            print(f'  ✓ {key}: {token[key]}')
            print(f'    Individual scopes:')
            for scope in token[key].split():
                print(f'      - {scope}')
        else:
            print(f'  ✓ {key}: {token[key]}')
    
    print()
    print('=' * 80)
    print('KEY FINDING:')
    if 'scope' in token:
        print('  ✅ rclone.conf DOES store scope information!')
        print(f'  Scope: {token[\"scope\"]}')
    else:
        print('  ❌ rclone.conf does NOT store scope information')
        print('  Available fields: ' + ', '.join(token.keys()))
    print('=' * 80)
    
except Exception as e:
    print(f'Error parsing token: {e}')
"
    else
        echo "❌ Could not extract token from config file"
    fi
    
    echo ""
    echo "🧹 Cleaning up temporary remote..."
    rclone config delete "$TEMP_REMOTE" 2>/dev/null
    
else
    echo ""
    echo "❌ Failed to create configuration"
    echo "See output above for details"
fi

echo ""
echo "================================================================================"
echo "Experiment complete!"
echo "================================================================================"


