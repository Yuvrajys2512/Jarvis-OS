"""
Extra JARVIS tools: weather, timers, file search, clipboard, screenshots, screen vision.
"""
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

# ── Active timers ──────────────────────────────────────────────────────────────

_timers: dict[str, threading.Timer] = {}


# ── Weather ───────────────────────────────────────────────────────────────────

def get_weather(location: str = "") -> str:
    """Fetch current weather using wttr.in (no API key needed)."""
    try:
        import urllib.request
        loc = location.strip().replace(" ", "+") if location.strip() else ""
        # Text-only format codes — no emoji, speaks cleanly via TTS
        fmt = "%l:+%C,+%t+(feels+like+%f),+humidity+%h,+wind+%w"
        url = f"https://wttr.in/{loc}?format={fmt}"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read().decode("utf-8").strip()
    except Exception as e:
        return f"Could not fetch weather: {e}"


# ── Timers ────────────────────────────────────────────────────────────────────

def set_timer(seconds: int, label: str = "Timer") -> str:
    """Set a countdown timer. JARVIS speaks an alert when it fires."""
    if label in _timers:
        _timers[label].cancel()

    def _fire():
        from core.text_to_speech import speak
        import server
        server.emit("status", value="speaking")
        speak(f"{label} is complete, sir.")
        server.emit("status", value="idle")
        _timers.pop(label, None)

    t = threading.Timer(seconds, _fire)
    t.daemon = True
    t.start()
    _timers[label] = t

    mins, secs = divmod(int(seconds), 60)
    if mins and secs:
        duration = f"{mins}m {secs}s"
    elif mins:
        duration = f"{mins} minute{'s' if mins != 1 else ''}"
    else:
        duration = f"{secs} second{'s' if secs != 1 else ''}"
    return f"Timer '{label}' set for {duration}."


def cancel_timer(label: str) -> str:
    """Cancel an active timer by label."""
    if label in _timers:
        _timers[label].cancel()
        _timers.pop(label)
        return f"Timer '{label}' cancelled."
    return f"No active timer named '{label}'."


def list_timers() -> str:
    """List all currently running timers."""
    if not _timers:
        return "No active timers."
    return "Active timers: " + ", ".join(_timers.keys())


# ── File search ───────────────────────────────────────────────────────────────

def search_files(name: str, folder: str = "") -> str:
    """
    Search for files by name on the computer.
    Searches Desktop, Documents, Downloads, and home dir by default.
    Returns up to 10 matches.
    """
    home = Path.home()
    roots = (
        [Path(folder)]
        if folder
        else [home / "Desktop", home / "Documents", home / "Downloads", home]
    )
    pattern = f"*{name}*" if "*" not in name else name
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob(pattern):
                found.append(str(p))
                if len(found) >= 10:
                    break
        except PermissionError:
            pass
        if len(found) >= 10:
            break

    if not found:
        return f"No files matching '{name}' found."
    return f"Found {len(found)} result(s):\n" + "\n".join(found)


# ── Clipboard ─────────────────────────────────────────────────────────────────

def read_clipboard() -> str:
    """Read the current text content of the clipboard."""
    try:
        result = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5,
        )
        text = result.stdout.strip()
        return text if text else "(clipboard is empty)"
    except Exception as e:
        return f"Could not read clipboard: {e}"


def write_clipboard(text: str) -> str:
    """Copy text to the clipboard."""
    try:
        # Write to a temp file so any characters are handled safely
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(text)
            tmp = f.name
        subprocess.run(
            ["powershell", "-command", f'Get-Content -Raw "{tmp}" | Set-Clipboard'],
            capture_output=True, text=True, timeout=5,
        )
        os.unlink(tmp)
        preview = text[:80] + ("..." if len(text) > 80 else "")
        return f"Copied to clipboard: {preview}"
    except Exception as e:
        return f"Could not write to clipboard: {e}"


# ── Screenshot & screen vision ────────────────────────────────────────────────

def take_screenshot(filename: str = "") -> str:
    """Take a screenshot of the entire screen and save it to the Desktop."""
    from PIL import ImageGrab
    path = filename or str(
        Path.home() / "Desktop" / f"jarvis_{int(time.time())}.png"
    )
    ImageGrab.grab().save(path)
    return f"Screenshot saved to: {path}"


def describe_screen(question: str = "What is on the screen right now?") -> str:
    """Take a screenshot and use Llama 4 Scout's vision to answer a question about it."""
    time.sleep(1.5)  # let any just-opened app finish loading
    import base64
    import io
    from PIL import ImageGrab
    from groq import Groq
    from config.settings import GROQ_API_KEY, GROQ_MODEL

    try:
        img = ImageGrab.grab()
        img.thumbnail((1280, 720))  # downscale for faster transfer
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}"
                    }},
                ],
            }],
            max_tokens=400,
        )
        return resp.choices[0].message.content or "Could not interpret the screen."
    except Exception as e:
        return f"Screen description failed: {e}"
