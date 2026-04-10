#!/bin/bash
# Sends "observe" command to HOI4 via AppleScript keystroke injection.
# Run this AFTER you're in a game (past the main menu, in the map view).

set -e

APP_NAME="hoi4"

echo "Sending 'observe' command to Hearts of Iron IV..."

# Open console (backtick key), type observe, press enter, close console
osascript <<'EOF'
tell application "System Events"
    tell process "hoi4"
        set frontmost to true
        delay 0.5
        -- Open console with backtick
        keystroke "`"
        delay 0.3
        -- Type observe
        keystroke "observe"
        delay 0.2
        -- Press enter
        key code 36
        delay 0.3
        -- Close console
        keystroke "`"
        delay 0.2
        -- Set speed 4 (press 4)
        keystroke "4"
    end tell
end tell
EOF

echo "Done! Game should now be in observer mode at speed 4."
echo "Run 'hoi-yo run --local' to start the agent loop."
