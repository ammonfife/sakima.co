---
name: mac-control
description: Control the local Mac desktop with scripts for windows, mouse, keyboard, focus changes, and screenshots.
---

# Mac Control Skill

Control the Mac desktop - windows, mouse, keyboard, screenshots.

## Setup

**Required for full control:**
1. System Settings → Privacy & Security → Accessibility
2. Enable Terminal (or your terminal app)
3. Enable cliclick if prompted

## Commands

### List Apps/Windows
```bash
python3 ~/clawd/scripts/mac-control.py windows
```

### Focus App
```bash
python3 ~/clawd/scripts/mac-control.py focus "Google Chrome"
python3 ~/clawd/scripts/mac-control.py focus "Safari" --title "GitHub"
```

### Screenshot
```bash
# Full screen
python3 ~/clawd/scripts/mac-control.py screenshot

# Specific output
python3 ~/clawd/scripts/mac-control.py screenshot -o /tmp/screen.png

# Interactive window select
python3 ~/clawd/scripts/mac-control.py screenshot --window
```

### Mouse
```bash
# Get position
python3 ~/clawd/scripts/mac-control.py pos

# Move to coordinates
python3 ~/clawd/scripts/mac-control.py move 500 300

# Click
python3 ~/clawd/scripts/mac-control.py click
python3 ~/clawd/scripts/mac-control.py click --x 500 --y 300
python3 ~/clawd/scripts/mac-control.py click --right        # Right click
python3 ~/clawd/scripts/mac-control.py click --double       # Double click
```

### Keyboard
```bash
# Type text
python3 ~/clawd/scripts/mac-control.py type "Hello world"
python3 ~/clawd/scripts/mac-control.py type "slow typing" --slow

# Press key
python3 ~/clawd/scripts/mac-control.py key return
python3 ~/clawd/scripts/mac-control.py key escape
python3 ~/clawd/scripts/mac-control.py key tab

# Hotkeys
python3 ~/clawd/scripts/mac-control.py hotkey cmd c          # Copy
python3 ~/clawd/scripts/mac-control.py hotkey cmd v          # Paste
python3 ~/clawd/scripts/mac-control.py hotkey cmd shift s    # Save as
python3 ~/clawd/scripts/mac-control.py hotkey cmd tab        # Switch app
```

## Key Names
- `return`, `enter`, `tab`, `escape`, `space`, `delete`
- `up`, `down`, `left`, `right`
- `cmd`, `ctrl`, `alt`, `shift`

## Combining Actions

Focus app and type:
```bash
python3 ~/clawd/scripts/mac-control.py focus "Notes"
sleep 0.5
python3 ~/clawd/scripts/mac-control.py type "Meeting notes from Big Mac"
python3 ~/clawd/scripts/mac-control.py key return
```

## Troubleshooting

**"assistive access" error:**
- System Settings → Privacy → Accessibility → enable Terminal

**Mouse/keyboard not working:**
- May need to enable cliclick in Accessibility settings
