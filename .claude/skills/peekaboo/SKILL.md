---
name: peekaboo
description: Capture and automate macOS UI with the Peekaboo CLI.
homepage: https://peekaboo.boo
metadata:
  {
    "openclaw":
      {
        "emoji": "👀",
        "os": ["darwin"],
        "requires": { "bins": ["peekaboo"] },
        "install":
          [
            {
              "id": "brew",
              "kind": "brew",
              "formula": "steipete/tap/peekaboo",
              "bins": ["peekaboo"],
              "label": "Install Peekaboo (brew)",
            },
          ],
      },
  }
---

# Peekaboo Skill

## USE THIS WHEN

- Automating any **macOS native app** (Finder, Safari, Messages, Telegram, System Preferences, etc.)
- Clicking UI elements you can't target by coordinates alone
- You need to know what's on screen before acting
- Interacting with menus, dialogs, windows, the Dock, menubar

## DO NOT USE WHEN

- You need cross-platform Python automation → use desktop-control skill instead
- The target is a web page you control via browser tool → use `browser` tool instead

---

## STEP 0: CHECK INSTALL

```bash
which peekaboo || brew install steipete/tap/peekaboo
```

If not installed and brew fails, tell the user: `brew tap steipete/tap && brew install peekaboo`

## STEP 1: CHECK PERMISSIONS (first time or if things fail)

```bash
peekaboo permissions
```

Peekaboo needs **Screen Recording** AND **Accessibility** permissions in System Settings > Privacy & Security. If either is missing, automation will silently fail or error. Do not skip this if you're seeing weird errors.

---

## THE GOLDEN WORKFLOW: See → Identify → Act

**Always follow this order. Never click blind.**

### 1. See the screen

```bash
# Take annotated screenshot — saves element IDs (B1, T2, etc.)
peekaboo see --annotate --path /tmp/snap.png
```

Then view the image:

```bash
open /tmp/snap.png
```

Or use the `image` tool to analyze it: `image(image="/tmp/snap.png", prompt="What element IDs are visible?")`

### 2. Identify the target element ID

The annotated image overlays IDs on every clickable element:

- `B1`, `B2` = buttons
- `T1`, `T2` = text fields
- `I1`, `I2` = images/icons

### 3. Act using the element ID

```bash
peekaboo click --on B2
peekaboo type "hello world" --on T1
peekaboo press tab
peekaboo press return
```

---

## TARGETING A SPECIFIC APP OR WINDOW

```bash
# See a specific app's window
peekaboo see --app "Safari" --annotate --path /tmp/snap.png

# See a specific window by title
peekaboo see --app "Safari" --window-title "Login" --annotate --path /tmp/snap.png

# Click inside a specific app
peekaboo click --on B1 --app "Safari"

# Type into a specific app
peekaboo type "username@example.com" --app "Safari"
```

---

## COMPLETE EXAMPLES

### Log into a web form (Safari)

```bash
peekaboo see --app Safari --annotate --path /tmp/snap.png
# Look at snap.png — find T1 (email field), T2 (password field), B1 (submit button)
peekaboo click --on T1 --app Safari
peekaboo type "user@example.com" --app Safari
peekaboo press tab
peekaboo type "mypassword" --app Safari
peekaboo click --on B1 --app Safari
```

### Open an app and do something

```bash
peekaboo app launch "TextEdit"
sleep 1
peekaboo see --app TextEdit --annotate --path /tmp/snap.png
peekaboo type "Hello world" --app TextEdit
peekaboo hotkey --keys "cmd,s"
```

### Click a menu item

```bash
peekaboo menu click --app Safari --item "New Window"
peekaboo menu click --app TextEdit --path "Format > Font > Show Fonts"
```

### Take a screenshot and analyze it

```bash
peekaboo image --mode screen --path /tmp/screen.png
# Or with AI analysis:
peekaboo see --mode screen --analyze "What is on the screen?"
```

### Launch a URL in Safari

```bash
peekaboo app launch "Safari" --open "https://example.com"
```

### Keyboard shortcuts

```bash
peekaboo hotkey --keys "cmd,c"          # Copy
peekaboo hotkey --keys "cmd,v"          # Paste
peekaboo hotkey --keys "cmd,shift,t"    # Reopen closed tab
peekaboo hotkey --keys "cmd,tab"        # Switch app
peekaboo press escape
peekaboo press return
peekaboo press tab --count 3
```

### Window management

```bash
peekaboo window focus --app Safari
peekaboo window maximize --app Safari
peekaboo window set-bounds --app Safari --x 0 --y 0 --width 1440 --height 900
peekaboo list windows --app Safari --json
```

---

## COMMON GOTCHAS

| Problem                         | Fix                                                                 |
| ------------------------------- | ------------------------------------------------------------------- |
| `peekaboo: command not found`   | `brew install steipete/tap/peekaboo`                                |
| Click does nothing              | Run `peekaboo permissions` — Accessibility likely missing           |
| Can't find element ID           | Re-run `peekaboo see --annotate` and open the PNG                   |
| Wrong window targeted           | Add `--app "AppName"` or `--window-title "Title"`                   |
| Element ID changes between runs | IDs are snapshot-based — re-run `see` if the UI changed             |
| Need to click coordinates       | `peekaboo click --coords 500,300` (fallback if no element ID works) |

---

## QUICK REFERENCE

```bash
peekaboo permissions                          # Check perms
peekaboo see --annotate --path /tmp/s.png    # Screenshot with element IDs
peekaboo list apps --json                    # List running apps
peekaboo list windows --app "App" --json     # List app windows
peekaboo app launch "AppName"                # Launch app
peekaboo app quit --app "AppName"            # Quit app
peekaboo click --on B1                       # Click element
peekaboo click --coords 500,300              # Click coordinates
peekaboo type "text" --return                # Type + press Return
peekaboo press tab                           # Press key
peekaboo hotkey --keys "cmd,c"               # Keyboard shortcut
peekaboo menu click --app App --item "Menu"  # Click menu
peekaboo scroll --direction down --amount 5  # Scroll
peekaboo image --mode screen --path /tmp/s.png  # Screenshot (no annotation)
```
