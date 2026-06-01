"""
JARVIS — Local Agentic AI Assistant
Run this file to start JARVIS. Say 'Jarvis' to activate.
The dashboard opens automatically at http://localhost:7777
"""
import sys
import ctypes
import random
import threading
import time

# Web results contain characters (₹, special spaces) the Windows cp1252 console
# can't encode. Without this, printing a result/response crashes the pipeline
# (and JARVIS says "I encountered an error" instead of answering). Make all
# console output UTF-8 and never fatal.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import server

_window = None


class _WebviewAPI:
    def minimize(self):
        if _window:
            _window.minimize()

    def toggle_fullscreen(self):
        if _window:
            _window.toggle_fullscreen()


def _shutdown():
    """Destroy the native window (causes webview.start() to return on main thread)."""
    global _window
    if _window:
        _window.destroy()


# Tools that open a persistent app window — JARVIS steps aside and stays aside
# (the app should remain visible in front after the command finishes).
_APP_OPEN_TOOLS = {"open_application"}

# Tools that do work in Chrome then return — JARVIS steps aside, reads results,
# then reclaims the top so the HUD is visible again.
_BROWSER_TOOLS = {"search_google", "open_url", "find_prices", "get_page_text"}


def _set_topmost(topmost: bool) -> None:
    """Pin JARVIS above all windows (True) or drop it so apps can appear in front (False)."""
    user32 = ctypes.windll.user32
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
    hwnd = user32.FindWindowW(None, "JARVIS")
    if hwnd:
        flag = HWND_TOPMOST if topmost else HWND_NOTOPMOST
        user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


def preload_models() -> None:
    print("Initialising JARVIS...")
    from core.speech_to_text import _get_model as load_stt
    from core.wake_word import _get_model as load_wake
    from core.agent import _get_client
    load_stt()
    load_wake()
    _get_client()
    print("All systems online.\n")


def run() -> None:
    from core.wake_word import wait_for_wake_word
    from core.speech_to_text import listen_and_transcribe
    from core.text_to_speech import speak
    from core.agent import process_instruction

    server.emit("status", value="idle")
    speak("Good evening. JARVIS is online and standing by.")

    while True:
        try:
            # Wait for wake word
            server.emit("status", value="idle")
            wait_for_wake_word()

            # Listen
            server.emit("status", value="listening")
            speak(random.choice([
                "Online. How can I assist you, sir?",
                "JARVIS online. What do you need?",
                "At your service. Go ahead.",
                "I'm listening. What's the task?",
                "Ready when you are, sir.",
            ]))
            command = listen_and_transcribe()

            if not command.strip():
                speak("I didn't catch that, sir. Please try again.")
                continue

            # Word-by-word reveal — show captured words on the HUD before processing
            words = command.strip().split()
            for i in range(len(words)):
                server.emit("partial", text=" ".join(words[: i + 1]))
                time.sleep(0.07)

            print(f"\nCommand: \"{command}\"")
            server.emit("user", text=command)

            # Shutdown phrase
            if any(w in command.lower() for w in ["goodbye jarvis", "jarvis sleep", "shut down", "exit"]):
                server.emit("status", value="idle")
                speak("Goodbye, sir. JARVIS signing off.")
                _shutdown()
                return

            # Think
            server.emit("status", value="thinking")
            print("Thinking...")

            response = process_instruction(command, _on_tool_start, _on_tool_end)

            # Speak
            server.emit("jarvis", text=response)
            server.emit("status", value="speaking")
            print(f"JARVIS: \"{response}\"\n")
            speak(response)

        except KeyboardInterrupt:
            speak("Shutting down. Goodbye, sir.")
            _shutdown()
            return
        except Exception as e:
            print(f"Error: {e}")
            server.emit("status", value="idle")
            speak("I encountered an error, sir. Standing by.")


# Brief spoken narration before each tool runs
_NARRATIONS = {
    "ask_researcher":     lambda a: "Allow me to research that, sir.",
    "open_application":   lambda a: f"Opening {a.get('name', 'that')} for you now.",
    "search_google":      lambda a: f"Right away, sir. Opening Chrome and searching for {a.get('query', 'that')}. Watch the screen.",
    "open_url":           lambda a: "Opening that up on screen now.",
    "find_prices":        lambda a: f"Let me pull up prices for {a.get('query', 'that')} on screen.",
    "get_page_text":      lambda a: "Bringing that page up to read it.",
    "get_weather":        lambda a: (f"Checking the weather in {a['location']}." if a.get('location') else "Checking the current weather."),
    "set_timer":          lambda a: f"Setting a timer for {a.get('seconds', 0)} seconds.",
    "cancel_timer":       lambda a: "Cancelling that timer.",
    "search_files":       lambda a: f"Searching your files for {a.get('name', 'that')}.",
    "write_clipboard":    lambda a: "Copying that to your clipboard.",
    "take_screenshot":    lambda a: "Taking a screenshot.",
    "describe_screen":    lambda a: "Let me take a look at your screen.",
    "run_terminal_command": lambda a: "Running that command.",
}


def _on_tool_start(agent: str, name: str, args: dict) -> None:
    """Before a tool runs: emit it to the HUD, speak its narration, and step aside
    if it opens a window so the app/browser appears in front of JARVIS."""
    from core.text_to_speech import speak as _speak
    if name.startswith("ask_"):
        server.emit("agent", name=name[4:], state="active")   # ignite the specialist's HUD panel
    server.emit("tool", name=name, args=args, agent=agent)
    narration_fn = _NARRATIONS.get(name)
    if narration_fn:
        try:
            line = narration_fn(args)
            if line:
                _speak(line)
        except Exception:
            pass
    if name in _APP_OPEN_TOOLS or name in _BROWSER_TOOLS:
        _set_topmost(False)   # step aside so the app/browser can appear on top


def _on_tool_end(agent: str, name: str, args: dict, result: str) -> None:
    """After a tool runs: browser tasks are done, so JARVIS reclaims the top to show
    their results. App-open tools intentionally leave the opened app in front."""
    if name in _BROWSER_TOOLS:
        _set_topmost(True)    # browser task done — JARVIS reclaims the top
    if name.startswith("ask_"):
        server.emit("agent", name=name[4:], state="idle")    # dim the specialist's HUD panel


def main() -> None:
    import webview
    global _window

    preload_models()
    print("Starting JARVIS dashboard...")
    server.launch()

    # Voice pipeline runs in background — pywebview must own the main thread
    pipeline = threading.Thread(target=run, daemon=True)
    pipeline.start()

    _window = webview.create_window(
        "JARVIS",
        "http://localhost:7777",
        fullscreen=True,
        frameless=True,
        on_top=True,             # sit above everything; steps aside only during tool execution
        background_color="#020608",
        js_api=_WebviewAPI(),
    )
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    main()
