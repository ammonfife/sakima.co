---
name: desktop-control
description: "Lightweight pointer to the canonical desktop-control-1.0.0 skill — advanced desktop automation with mouse, keyboard, screen control, and autonomous AI agent capabilities."
---

# Desktop Control (stub)

This is a stub. The full skill lives at `~/.openclaw/skills/desktop-control-1.0.0/` and is also installed locally as `desktop-control-1.0.0`. Use that one for the complete API reference, AI agent guide, and quick reference.

## Quick recap

```python
from skills.desktop_control import DesktopController
dc = DesktopController(failsafe=True)
dc.move_mouse(500, 300, duration=0.5)
dc.click(500, 300)
dc.type_text("Hello World", wpm=60)
dc.screenshot(filename="capture.png")
```

## AI Agent (autonomous)

```python
from skills.desktop_control.ai_agent import AIDesktopAgent
agent = AIDesktopAgent()
agent.execute_task("Open Calculator")
```

## Dependencies

```bash
pip install pyautogui pillow opencv-python pygetwindow pyperclip
```
