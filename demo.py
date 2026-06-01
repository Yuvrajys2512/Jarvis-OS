"""
JARVIS Demo
Choreographed showcase: idle → wake → open project + terminal → YouTube search → Notepad
Usage: python demo.py
"""
import os
import sys
import json
import time
import random
import threading
import subprocess
import pyautogui
import server
from pathlib import Path

_window = None

DEMO_COMMAND = (
    "Open my last project and a terminal. "
    "Find the latest MrBeast video on YouTube "
    "and write the title in Notepad."
)


# ── Win32 window snapping ──────────────────────────────────────────────────────

_PS_W32 = r'''
try {
  Add-Type -TypeDefinition @"
  using System; using System.Runtime.InteropServices;
  public class DemoWin32 {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr z, int x, int y, int cx, int cy, uint f);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  }
"@
} catch {}
'''

def _snap(title_regex: str, x: int, y: int, w: int, h: int, tries: int = 14) -> bool:
    """Find window whose title matches regex and snap it to (x,y,w,h). Retries while window opens."""
    ps = f'''
{_PS_W32}
$p = Get-Process | Where-Object {{ $_.MainWindowTitle -match "{title_regex}" }} | Sort-Object StartTime -Descending | Select-Object -First 1
if ($p) {{
    [DemoWin32]::ShowWindow($p.MainWindowHandle, 9)
    [DemoWin32]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, {x}, {y}, {w}, {h}, 0x0054)
    Write-Output "ok"
}}
'''
    for _ in range(tries):
        r = subprocess.run(['powershell', '-Command', ps], capture_output=True, text=True, timeout=10)
        if 'ok' in r.stdout:
            return True
        time.sleep(0.5)
    return False


def _left_rect(split: str = 'full'):
    """Return (x, y, w, h) for a region in the left 62% of screen."""
    from tools.browser import JARVIS_FRACTION
    sw, sh = pyautogui.size()
    aw = int(sw * (1 - JARVIS_FRACTION))
    ah = sh - 52   # subtract taskbar
    if split == 'top':    return 0, 0, aw, ah * 55 // 100
    if split == 'bottom': return 0, ah * 55 // 100, aw, ah - ah * 55 // 100
    return 0, 0, aw, ah


# ── Recent project detection ───────────────────────────────────────────────────

def _recent_project() -> str:
    """Try Antigravity IDE storage first, then VS Code."""
    candidates = [
        Path(os.environ["APPDATA"]) / "Antigravity"          / "User" / "globalStorage" / "storage.json",
        Path(os.environ["APPDATA"]) / "Antigravity Code"     / "User" / "globalStorage" / "storage.json",
        Path(os.environ["APPDATA"]) / "Code"                 / "User" / "globalStorage" / "storage.json",
    ]
    for storage in candidates:
        if not storage.exists():
            continue
        try:
            data = json.loads(storage.read_text(encoding="utf-8"))
            for entry in data.get("openedPathsList", {}).get("workspaces3", []):
                uri = entry if isinstance(entry, str) else entry.get("folderUri", "")
                if uri.startswith("file:///"):
                    path = uri.replace("file:///", "").replace("/", "\\")
                    if os.path.isdir(path):
                        return path
        except Exception:
            pass
    return ""


# ── YouTube: MrBeast latest video via RSS (reliable, no Playwright needed) ────

def _mrbeast_latest() -> str:
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        ATOM = "http://www.w3.org/2005/Atom"
        # MrBeast's channel ID — hardcoded, doesn't change
        url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCX6OQ3DkcsbYNE6H8uQQuVA"
        with urllib.request.urlopen(url, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        entry = root.find(f"{{{ATOM}}}entry")
        if entry is not None:
            title_el = entry.find(f"{{{ATOM}}}title")
            if title_el is not None and title_el.text:
                return title_el.text.strip()
    except Exception:
        pass
    return "I Survived 100 Days in the World's Hardest Game"  # demo fallback


# ── Demo sequence ──────────────────────────────────────────────────────────────

def _demo():
    from core.text_to_speech import speak
    import tools.browser as bm

    # ── Phase 1: Idle — show the dim, quiet state ──────────────────────────────
    server.emit("status", value="idle")
    time.sleep(4)

    # ── Phase 2: Wake word → shockwave activation ──────────────────────────────
    # Emitting "listening" from idle triggers the JS activating→listening path (1.9s shockwave)
    server.emit("status", value="listening")
    time.sleep(1.9)   # let shockwave animation finish
    server.emit("user", text="Jarvis, you up?")
    speak(random.choice([
        "Always, sir. What do you need?",
        "Good evening. Ready when you are.",
        "Online and standing by. Go ahead, sir.",
    ]))
    time.sleep(0.8)

    # ── Phase 3: User command appears ─────────────────────────────────────────
    server.emit("user", text=DEMO_COMMAND)
    time.sleep(0.9)
    server.emit("status", value="thinking")
    time.sleep(0.7)

    # ── Phase 4: Open last project ─────────────────────────────────────────────
    server.emit("tool", name="open_application", args={"name": "last project"})
    speak("Opening your last project, sir.")

    project = _recent_project()
    if project:
        # Try editors in preference order
        for editor in ("antigravity", "code", "cursor"):
            probe = subprocess.run(f"where {editor}", shell=True, capture_output=True)
            if probe.returncode == 0:
                subprocess.Popen(f'{editor} "{project}"', shell=True)
                break
        time.sleep(5)
        x, y, w, h = _left_rect('top')
        _snap(r"Antigravity|Visual Studio Code|Code — ", x, y, w, h)

    # ── Phase 5: Open terminal in project directory ────────────────────────────
    server.emit("tool", name="run_terminal_command", args={"command": "start terminal"})
    speak("Starting the terminal.")

    start_dir = f' -d "{project}"' if project else ""
    subprocess.Popen(f"wt.exe{start_dir}", shell=True)
    time.sleep(2.8)
    tx, ty, tw, th = _left_rect('bottom')
    _snap(r"Windows Terminal|Terminal", tx, ty, tw, th)
    time.sleep(1.2)

    # ── Phase 6: Open YouTube MrBeast (visible Chrome, theatrical typing) ──────
    server.emit("tool", name="open_url", args={"url": "youtube.com/@MrBeast"})
    speak("Pulling up MrBeast's channel on YouTube.")

    bm._chrome_count += 1
    subprocess.Popen("start chrome --new-window", shell=True)
    time.sleep(2.5)
    bm._arrange()           # snap Chrome into left-area tile
    time.sleep(0.5)
    bm._focus_slot_and_type("youtube.com/@MrBeast/videos")
    time.sleep(5)           # YouTube loads visually while we fetch via RSS

    # ── Phase 7: Fetch latest title via RSS (fast, while Chrome already open) ──
    server.emit("tool", name="get_page_text", args={"url": "youtube.com/@MrBeast"})
    speak("Scanning his channel for the latest upload, sir.")
    title = _mrbeast_latest()
    time.sleep(0.8)

    # ── Phase 8: Open Notepad ─────────────────────────────────────────────────
    server.emit("tool", name="open_application", args={"name": "notepad"})
    speak("Opening Notepad.")

    subprocess.Popen("notepad.exe", shell=True)
    time.sleep(2)

    # Float Notepad centered in the left area, not full height so Chrome stays visible
    sw, sh = pyautogui.size()
    from tools.browser import JARVIS_FRACTION
    aw = int(sw * (1 - JARVIS_FRACTION))
    nw = int(aw * 0.72)
    nh = int((sh - 52) * 0.30)
    nx = (aw - nw) // 2
    ny = int((sh - 52) * 0.34)
    found = _snap("Notepad", nx, ny, nw, nh, tries=14)
    time.sleep(0.5)

    # Focus the Notepad text area
    pyautogui.click(nx + nw // 2, ny + nh // 2)
    time.sleep(0.45)

    # ── Phase 9: Type title letter by letter ──────────────────────────────────
    server.emit("tool", name="write_clipboard", args={"text": title})
    short = title[:55] + ("..." if len(title) > 55 else "")
    speak(f"Writing the title now. It reads: {short}.")

    for ch in title:
        if ch.isascii() and ch.isprintable():
            pyautogui.write(ch, interval=0)
            time.sleep(0.072)
        elif ch == '\n':
            pyautogui.press('enter')
            time.sleep(0.1)
        # skip non-ASCII characters to avoid garbled output

    time.sleep(0.5)

    # ── Phase 10: Summary ─────────────────────────────────────────────────────
    reply = f'Done, sir. Latest MrBeast upload: "{title}". Your project is open, terminal is ready, and the title is in Notepad.'
    server.emit("jarvis", text=reply)
    server.emit("status", value="speaking")
    speak(f'All done, sir. His latest upload is "{short}". Project open, terminal ready, title written.')
    time.sleep(6)
    server.emit("status", value="idle")


# ── Entry point ────────────────────────────────────────────────────────────────

class _API:
    def toggle_fullscreen(self):
        if _window:
            _window.toggle_fullscreen()


def main():
    import webview
    global _window

    print("Starting JARVIS demo...")
    server.launch()
    print("Server up. Demo begins in ~2s.\n")

    threading.Thread(target=_demo, daemon=True).start()

    _window = webview.create_window(
        "JARVIS",
        "http://localhost:7777",
        fullscreen=True,
        frameless=True,
        background_color="#020608",
        js_api=_API(),
    )
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    main()
