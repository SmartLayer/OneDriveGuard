#!/usr/bin/env python3
"""
Use rclone authorize to get a fresh token and examine it.

This will use rclone's own OAuth flow (which works with personal accounts)
and then we can inspect what Microsoft actually returns.
"""

import subprocess
import json
import sys

print("=" * 80)
print("Using rclone authorize to get a fresh token")
print("=" * 80)
print()
print("This will:")
print("  1. Run 'rclone authorize onedrive'")
print("  2. rclone will launch your browser")
print("  3. You authenticate with your PERSONAL Microsoft account")
print("  4. rclone captures the token response")
print("  5. We examine what Microsoft returned")
print()
print("Press Enter to start, or Ctrl+C to cancel...")
try:
    input()
except KeyboardInterrupt:
    print("\n\nCancelled")
    sys.exit(0)

print("\n🚀 Running: rclone authorize onedrive")
print()
print("=" * 80)
print("NOTE: Your browser will open. Sign in with your PERSONAL Microsoft account.")
print("=" * 80)
print()

try:
    # Run rclone authorize
    result = subprocess.run(
        ['rclone', 'authorize', 'onedrive'],
        capture_output=True,
        text=True,
        timeout=180  # 3 minute timeout
    )
    
    if result.returncode == 0:
        print("\n✅ Authorization successful!")
        print()
        
        # The output should contain JSON token data
        output = result.stdout
        
        # Try to find JSON in the output
        # rclone outputs: Paste the following into your remote machine --->
        # {token json}
        # <---End paste
        
        print("📋 Raw output:")
        print("-" * 80)
        print(output)
        print("-" * 80)
        print()
        
        # Try to extract JSON
        import re
        json_match = re.search(r'\{[^{}]*"access_token"[^{}]*\}', output, re.DOTALL)
        
        if json_match:
            token_json = json_match.group(0)
            try:
                token_data = json.loads(token_json)
                
                print("=" * 80)
                print("🔍 TOKEN ANALYSIS")
                print("=" * 80)
                print()
                
                print("Fields in token response:")
                for key in sorted(token_data.keys()):
                    if key == 'access_token':
                        val = token_data[key]
                        print(f"  ✓ {key}: {val[:30]}...{val[-20:]} (length: {len(val)})")
                    elif key == 'refresh_token':
                        val = token_data[key]
                        print(f"  ✓ {key}: {val[:30]}... (length: {len(val)})")
                    elif key == 'scope':
                        print(f"  ✓ {key}: {token_data[key]}")
                        print(f"    Individual scopes:")
                        for scope in token_data[key].split():
                            print(f"      - {scope}")
                    else:
                        print(f"  ✓ {key}: {token_data[key]}")
                
                print()
                print("=" * 80)
                print("⭐ KEY QUESTION: Is 'scope' field present?")
                print("=" * 80)
                
                if 'scope' in token_data:
                    print("  ✅ YES! Scope field IS present in the token response!")
                    print(f"  Scope: {token_data['scope']}")
                    print()
                    print("  This means:")
                    print("    - Microsoft DOES return scope information")
                    print("    - We CAN save it to token.json")
                    print("    - We CAN use it to detect token capabilities")
                else:
                    print("  ❌ NO - Scope field is NOT in the token response")
                    print()
                    print("  Available fields: " + ", ".join(token_data.keys()))
                    print()
                    print("  This would mean we must use the heuristic method.")
                
                print("=" * 80)
                
            except json.JSONDecodeError as e:
                print(f"❌ Could not parse JSON: {e}")
        else:
            print("⚠️  Could not find JSON token in output")
            print("   Looking for alternative formats...")
    
    else:
        print(f"\n❌ rclone authorize failed with exit code: {result.returncode}")
        print(f"\nStdout:\n{result.stdout}")
        print(f"\nStderr:\n{result.stderr}")

except subprocess.TimeoutExpired:
    print("\n❌ Timeout waiting for authorization (3 minutes)")
    print("   Did you complete the authentication in the browser?")
except FileNotFoundError:
    print("\n❌ rclone command not found")
    print("   Please install rclone first")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()


