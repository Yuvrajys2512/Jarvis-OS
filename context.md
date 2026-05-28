# JARVIS — Project Context

> Read this file at the start of any new session. It replaces the need to grep every file or re-explain the project.

---

## What Is This

JARVIS is a local, agentic AI voice assistant inspired by Iron Man — fully offline except for the Groq API call. You say "Jarvis", it wakes, listens, thinks using an LLM with tool use, acts on the computer, and speaks back. A browser dashboard at `http://localhost:7777` shows real-time state changes with dramatic Iron Man-style visuals.

**Core UX principle (non-negotiable):** The #1 goal is to **look cool**. Every action must be theatrical and step-by-step visible. States must be unmissably different. Subtle is never acceptable.

---

## How to Run

```
python main.py
```

Preloads all models, starts FastAPI dashboard, opens browser, enters wake-word loop.

**Dashboard:** `http://localhost:7777`
**Wake word:** Say anything containing "Jarvis" (e.g. "Jarvis wake up", "hey Jarvis")
**Shutdown:** Say "goodbye jarvis", "jarvis sleep", "shut down", or "exit"

---

## Current Status

**Phase 10 in progress — UI overhaul complete, needs real-world WS testing.**

| What | Status |
|---|---|
| Full voice pipeline (wake → STT → LLM → TTS) | Done |
| Dashboard with dramatic state-based UI | Done — keyboard-tested, WS untested live |
| 15 tools across system, browser, extras | Done |
| Window tile system (Chrome doesn't overlap JARVIS) | Done — untested |
| ElevenLabs voice upgrade | Not started |
| Antigravity IDE recent projects | Not started — `get_recent_vs_code_project()` only works for VS Code |

---

## Directory Structure

```
JARVIS/
├── main.py               # Entry point — preload, server, main loop, tool narrations
├── server.py             # FastAPI + WebSocket dashboard server
├── requirements.txt
├── .env                  # API keys (not committed)
├── context.md            # This file
│
├── config/
│   └── settings.py       # All tuneable constants
│
├── core/
│   ├── wake_word.py      # Whisper base, 2s chunks, triggers on "jarvis"
│   ├── speech_to_text.py # Silence-gated mic recording + Whisper transcription
│   ├── text_to_speech.py # edge-tts → PyAV decode → sounddevice playback
│   └── agent.py          # Groq/Llama4 brain with manual tool-calling loop + history
│
├── tools/
│   ├── system.py         # open_application, run_terminal_command, get_recent_vs_code_project
│   ├── browser.py        # open_url, search_google, get_page_text, find_prices + TILE SYSTEM
│   └── extras.py         # weather, timers, file search, clipboard, screenshot, screen vision
│
└── static/
    └── index.html        # Full Iron Man HUD (canvas particles + CSS state machine)
```

---

## Full Pipeline

```
1. wait_for_wake_word()   → Whisper base 2s chunks, triggers on "jarvis"
2. listen_and_transcribe() → silence-gated recording, Whisper beam_size=5
3. _patch_agent_for_dashboard() → monkey-patches _execute_tool (once, guarded)
4. process_instruction(command) → Groq tool-calling loop until plain text
5. speak(response)        → edge-tts → PyAV → sounddevice

Dashboard events at each step:
  server.emit("status", value="idle|listening|thinking|speaking")
  server.emit("user",   text=command)
  server.emit("jarvis", text=response)
  server.emit("tool",   name=name, args=args)
```

---

## Dashboard UI — `static/index.html`

Pure HTML/CSS/JS, no framework. Canvas 2D + HTML HUD overlay.

### Visual States (each is unmissably different)

| State | Background | Edge Glow | Label |
|---|---|---|---|
| **idle** | `#020608` near-black | None | dim "IDLE" at 18% opacity |
| **listening** | `#001810` dark green | Pulsing green `0.55→0.75 alpha` | "LISTENING_" 96px neon green |
| **thinking** | `#140b00` dark amber | Pulsing amber `0.50→0.70 alpha` | "PROCESSING" amber, rapid pulse animation |
| **speaking** | `#000e1f` dark navy | Pulsing blue `0.55→0.70 alpha` | "RESPONDING" 96px electric blue |

### State Transitions (JavaScript)
```javascript
// Triggered by WebSocket events from Python server.emit()
status=listening + STATE===idle  → 'activating' (shockwave burst, 1.9s) → 'listening'
status=listening + STATE!==idle  → 'listening'
status=thinking                  → 'thinking'
status=speaking                  → 'speaking'
status=idle                      → 'idle'
```

### Keyboard Test Shortcuts
Press these in the browser to manually trigger states without running JARVIS:
- `1` → idle
- `2` → listening
- `3` → thinking
- `4` → speaking

### WebSocket Indicator
Top-right corner has a small dot: **red = disconnected**, **green = connected**.

### Canvas Elements
- 280 Fibonacci-sphere particles with spring physics (k=4, damp=2)
- Hex grid background (sz=58, alpha 0.07)
- 3 tilted orbital rings with dashed stroke
- 64-bar waveform ring (active in listening/speaking)
- 22 falling hex data streams
- Left/right side HUD panels (Neural Link bars, System Status)
- Shockwave rings on wake-word activation
- Streaming text for JARVIS response (42 chars/sec)

### Layer z-index Order
```
z-index 0:  canvas (particles, hex grid, orb, rings)
z-index 2:  #colorLayer (radial tint overlay per state)
z-index 5:  body::after (inset edge glow per state)
z-index 10: #hud (corners, labels, transcript, top bar)
```

---

## Tools — All 15

### System (`tools/system.py`)
| Tool | Description |
|---|---|
| `open_application` | Opens app by name — uses APP_ALIASES dict |
| `run_terminal_command` | Shell command, 30s timeout, blocklist for destructive commands |
| `get_recent_vs_code_project` | Reads VS Code storage.json — **doesn't work for Antigravity IDE** |

### Browser (`tools/browser.py`) — has window tile system
| Tool | Description |
|---|---|
| `search_google` | Opens new Chrome window (tiled), theatrically types query, presses Enter |
| `open_url` | Opens new Chrome window (tiled), types URL |
| `get_page_text` | Headless Playwright, returns first 3000 chars of body text |
| `find_prices` | Headed Playwright (off-screen tiny window), Bing Shopping, `.br-item` selectors |

**Window tile system:** `JARVIS_FRACTION = 0.38` reserves right 38% for dashboard. Each new Chrome window increments `_chrome_count`. `_arrange()` uses PowerShell + Win32 `SetWindowPos` to tile ALL Chrome windows (excluding ones with "JARVIS|localhost|7777" in title) into the left 62%. `reset_layout()` resets count.

**Theatrical typing:** `pyautogui.write(word, interval=0.07)` word-by-word with 0.16s gaps between words. Clicks into tile's address bar at `y=45` from window top.

### Extras (`tools/extras.py`)
| Tool | Description |
|---|---|
| `get_weather` | wttr.in text-only format (no emoji — avoids cp1252 encode error on Windows) |
| `set_timer` | threading.Timer, speaks alert when fires, stored in `_timers` dict |
| `cancel_timer` | Cancels by label |
| `list_timers` | Lists active timer labels |
| `search_files` | pathlib.rglob on Desktop/Documents/Downloads/home, max 10 results |
| `read_clipboard` | PowerShell `Get-Clipboard` |
| `write_clipboard` | Writes to temp file → `Get-Content -Raw | Set-Clipboard` |
| `take_screenshot` | PIL.ImageGrab → Desktop with timestamp |
| `describe_screen` | Screenshot → base64 → Groq vision API (Llama 4 Scout multimodal) |

---

## `main.py` — Key Details

### Tool Narrations
Before each tool runs, JARVIS speaks a brief narration:
```python
_NARRATIONS = {
    "open_application":   lambda a: f"Opening {a.get('name', 'that')}.",
    "search_google":      lambda a: f"Pulling up a search for {a.get('query', 'that')}.",
    "open_url":           lambda a: "Opening that in your browser.",
    "find_prices":        lambda a: f"Checking prices for {a.get('query', 'that')}.",
    "get_weather":        lambda a: (f"Checking the weather in {a['location']}." if a.get('location') else "Checking the current weather."),
    "describe_screen":    lambda a: "Let me take a look at your screen.",
    ...
}
```
`_patch_agent_for_dashboard()` monkey-patches `core.agent._execute_tool` to: emit WebSocket tool event → speak narration → call original.

### Wake Response (random)
```python
random.choice(["Online. How can I assist you, sir?", "JARVIS online. What do you need?", ...])
```

---

## `server.py` — Key Details

- FastAPI on `127.0.0.1:7777`, runs in daemon thread
- `emit(event_type, **kwargs)` — thread-safe via `asyncio.run_coroutine_threadsafe`
- WebSocket `/ws` keeps alive with 20s ping
- Serves `static/index.html` at `/`

---

## `core/agent.py` — Key Details

- `SYSTEM_PROMPT` — JARVIS persona (formal, "sir", dry wit, concise, always uses tools)
- `TOOL_DEFINITIONS` — all 15 tools registered with the model
- `_conversation` — in-memory list, session-scoped context window
- `process_instruction()` — manual tool-calling loop (no framework), runs until no more `tool_calls`
- `_execute_tool()` — routes tool name → function; monkey-patched by `main.py`

---

## Config (`config/settings.py`)

| Constant | Value | Notes |
|---|---|---|
| `GROQ_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | Llama 4, multimodal, tool use |
| `WHISPER_MODEL_SIZE` | `"base"` | Both wake word and STT |
| `TTS_VOICE` | `"en-GB-RyanNeural"` | British male, closest to Jarvis |
| `SILENCE_THRESHOLD` | `0.005` | RMS below this = silence |
| `SILENCE_DURATION` | `2.0` | Seconds of silence to stop recording |

---

## Known Issues / Gotchas

| Problem | Decision / Status |
|---|---|
| Gemini API free tier = 0 in India | Using Groq + Llama 4 Scout instead |
| pygame no Python 3.14 wheel | Using PyAV + sounddevice for audio |
| Bot detection on price search | `find_prices` uses headed Playwright + Bing |
| Antigravity IDE recent projects | `get_recent_vs_code_project()` reads VS Code's storage.json — won't work for Antigravity. Fix pending. |
| Weather wttr.in emoji encode error | Use text-only format codes `%l:+%C,+%t...` not `?format=3` |
| State UI not changing before | CSS was too subtle (glow at 0.10 alpha). Fixed — now 0.55-0.75 alpha with background tint. |
| WS events not confirmed live | Keyboard shortcuts (1-4) confirm CSS works. Real WS drive untested — check green dot in top-right. |
| Chrome window tile click misses | `y=45` targets Chrome address bar from window top. Adjust if Chrome opens with different chrome height. |

---

## What To Work On Next

1. **Verify live WS state changes** — run JARVIS, trigger wake word, confirm green dot is on and states transition automatically (not just keyboard shortcuts)
2. **Antigravity IDE support** — find where Antigravity stores recent projects and update `get_recent_vs_code_project()`
3. **ElevenLabs voice upgrade** — swap `edge-tts` for a proper Jarvis-sounding voice
4. **JARVIS center text color** — make the "JARVIS" canvas text change color to match the active state accent
5. **`reset_layout()` command** — wire "reset layout" voice command to `browser.reset_layout()` so tile counter resets
6. **Persistent memory** — JARVIS currently has no memory across sessions (conversation history resets on restart)

---

## Environment

- Python 3.14, Windows 11
- Git branch: `main`
- Run: `python main.py` from project root
- API keys in `.env` (GROQ_API_KEY required, GEMINI_API_KEY unused)
