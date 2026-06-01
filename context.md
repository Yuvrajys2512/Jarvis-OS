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

**Phase 11 — backdrop display model + visible Playwright browser.**

| What | Status |
|---|---|
| Full voice pipeline (wake → STT → LLM → TTS) | Done |
| Dashboard with dramatic state-based UI | Done — keyboard-tested, WS untested live |
| 16 tools across system, browser, extras | Done |
| **Backdrop model** — JARVIS runs behind, apps open in the foreground over it | Done |
| **Visible browser** — dedicated JARVIS Chrome profile, on-screen typing, reads results | Done — search tested live |
| ElevenLabs voice upgrade | Not started |
| Antigravity IDE recent projects | Not started — `get_recent_vs_code_project()` only works for VS Code |

### Display model — TOPMOST toggle (Phase 11)
The HUD is created with `on_top=True` (HWND_TOPMOST) — always visible above everything. When a foreground tool runs (`open_application`, `search_google`, `open_url`, `find_prices`, `get_page_text`), `_set_topmost(False)` drops JARVIS to NOTOPMOST so Chrome/apps appear in front. `_set_topmost(True)` restores JARVIS on top once the tool finishes. The old `_keep_in_background` thread (HWND_BOTTOM every 2.5s) and the left-62%/right-38% tile system are retired for the live assistant (kept only for `demo.py`).

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
│   ├── agent_base.py     # reusable Agent class — the tool-calling loop + per-agent history
│   ├── agent.py          # ORCHESTRATOR: JARVIS persona + non-browser tools + ask_researcher
│   └── agents/
│       └── researcher.py # Researcher specialist — owns the browser tools (web research)
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
3. process_instruction(command, _on_tool_start, _on_tool_end)
     → orchestrator Agent runs the Groq tool-calling loop until plain text;
       the hooks narrate each tool, emit dashboard events, and toggle window stacking
4. speak(response)        → edge-tts → PyAV → sounddevice

Dashboard events at each step:
  server.emit("status", value="idle|listening|thinking|speaking")
  server.emit("user",   text=command)
  server.emit("jarvis", text=response)
  server.emit("tool",   name=name, args=args, agent=agent)   # agent = which agent ran it
  server.emit("agent",  name=specialist, state="active|idle")  # multi-agent dispatch → HUD agent rail
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

## Tools — All 16

### System (`tools/system.py`)
| Tool | Description |
|---|---|
| `open_application` | Opens app by name — uses APP_ALIASES dict |
| `run_terminal_command` | Shell command, 30s timeout, blocklist for destructive commands |
| `get_recent_vs_code_project` | Reads VS Code storage.json — **doesn't work for Antigravity IDE** |

### Browser (`tools/browser.py`) — visible Playwright Chrome (dedicated profile)
| Tool | Description |
|---|---|
| `search_google` | Visible Chrome → Google → types query letter-by-letter → Enter → **returns results text** so JARVIS answers with real numbers |
| `find_prices` | Same visible flow, query suffixed with "price" |
| `open_url` | Navigates the visible window to a URL |
| `get_page_text` | Navigates the visible window to a URL, returns first 3000 chars of body text |
| `close_browser` | Closes the JARVIS Chrome window |

**Browser engine:** One persistent, visible Chrome driven by Playwright via `launch_persistent_context` with `channel="chrome"` and a dedicated profile at `~/.jarvis/chrome-profile`. Because it's one persistent profile, the **profile picker / "choose an account" screen never appears** — sign into Google once and it's remembered. The page/context is cached in module globals (`_pw`, `_ctx`, `_page`) and reused across the session; `_get_page()` relaunches if the user closed the window. `atexit` closes it on shutdown.

**Anti-bot:** `ignore_default_args=["--enable-automation"]` + `--disable-blink-features=AutomationControlled` strip the automation tells that otherwise trigger Google's "unusual traffic" wall. `_dismiss_google_consent()` clicks through the cookie/consent dialog.

**Theatrical typing:** `locator.press_sequentially(query, delay=85)` types into the real Google search box one char at a time, on screen. `_read_results()` pulls the answer from `#search`/`#rso`/`#center_col`.

**Legacy tile helpers** (`_arrange`, `_slots`, `_focus_slot_and_type`, `JARVIS_FRACTION`, etc.) remain at the bottom of the file but are used **only by `demo.py`**.

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
`main.py` passes `_on_tool_start` / `_on_tool_end` into `process_instruction()`. Before each tool: emit WebSocket tool event → speak narration → step aside if it opens a window. After browser tools: JARVIS reclaims the top. (This replaced the old `_patch_agent_for_dashboard` monkey-patch.)

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

## `core/agent.py` — Key Details (the Orchestrator)

- `SYSTEM_PROMPT` — JARVIS persona (formal, "sir", dry wit, concise, always uses tools)
- `TOOL_DEFINITIONS` — all 16 tools registered with the model
- `_execute_tool(name, args)` — routes tool name → function (lazy imports)
- `_get_orchestrator()` — builds/caches the single `Agent` ("jarvis") holding every tool via
  `_execute_tool`; its `.history` IS the session-scoped memory (replaces the old `_conversation`)
- `process_instruction(text, on_tool_start, on_tool_end)` — delegates to the orchestrator's
  `run()`. Stage 2+ splits tools into specialist sub-agents (agents-as-tools)

## `core/agent_base.py` — the Agent class (multi-agent foundation)

- `Agent(name, system_prompt, tools, dispatch, model, client_getter)` — each has its own `history`
- `run(text, on_tool_start, on_tool_end)` — the manual Groq tool-calling loop, lifted verbatim
  from the old `process_instruction`; the two hooks fire around each tool. One class powers every
  agent: a specialist is just an `Agent` with a narrower prompt + tool set, called by the
  orchestrator through an `ask_<specialist>` dispatch entry.
- `dispatch(name, args, on_tool_start, on_tool_end)` — a delegating tool (ask_researcher) threads
  the hooks into its sub-agent's `run()`, so narration + HUD events stay alive one level down.

## `core/agents/researcher.py` — first specialist (Stage 2, done)

- The **Researcher** owns the 5 browser tools (`search_google`, `open_url`, `find_prices`,
  `get_page_text`, `close_browser`) + a research-tuned prompt. `ask_researcher(task, hooks)` runs
  its own tool loop and returns synthesized findings for JARVIS to speak.
- The orchestrator no longer holds the browser tools — it has one `ask_researcher` tool whose
  dispatch calls the Researcher. Hooks are threaded down so browser tools still narrate + drive
  the HUD when the *Researcher* (not JARVIS) calls them.
- `main.py` emits `server.emit("agent", name="researcher", state=active/idle)` around the
  delegation, igniting the **agent rail** in the HUD (right-center: RESEARCHER active; OPERATOR /
  VISION / SCHEDULER shown as offline placeholders for future specialists).

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
| Google "unusual traffic" wall | Fixed — strip `--enable-automation` + disable `AutomationControlled` blink feature. Verified: live gold-price search reads real results. |
| Account/profile chooser got stuck | Fixed — dedicated persistent Chrome profile means one profile, no picker ever. Sign into Google once. |
| Actions happened off-screen | Fixed — backdrop model + visible Playwright window; `find_prices` no longer uses a 1×1 off-screen window |
| Web results crash cp1252 console | Fixed — `main.py` reconfigures stdout/stderr to UTF-8 with `errors="replace"` |
| Antigravity IDE recent projects | `get_recent_vs_code_project()` reads VS Code's storage.json — won't work for Antigravity. Fix pending. |
| Weather wttr.in emoji encode error | Use text-only format codes `%l:+%C,+%t...` not `?format=3` |
| State UI not changing before | CSS was too subtle (glow at 0.10 alpha). Fixed — now 0.55-0.75 alpha with background tint. |
| WS events not confirmed live | Keyboard shortcuts (1-4) confirm CSS works. Real WS drive untested — check green dot in top-right. |
| Chrome window tile click misses | Legacy (`demo.py` only). Live assistant uses Playwright element targeting, not blind `y=45` clicks. |

---

## What To Work On Next

1. **Verify live WS state changes** — run JARVIS, trigger wake word, confirm green dot is on and states transition automatically (not just keyboard shortcuts)
2. **Antigravity IDE support** — find where Antigravity stores recent projects and update `get_recent_vs_code_project()`
3. **ElevenLabs voice upgrade** — swap `edge-tts` for a proper Jarvis-sounding voice
4. **JARVIS center text color** — make the "JARVIS" canvas text change color to match the active state accent
5. **First-run Google sign-in** — the dedicated profile starts logged out; plain search works, but sign into Google once in the JARVIS Chrome window for personalised results
6. **Persistent memory** — JARVIS currently has no memory across sessions (conversation history resets on restart)
7. **Live end-to-end run** — browser flow verified standalone; still want a full voice run (wake → "open chrome and search X" → watch it → spoken answer)

---

## Environment

- Python 3.14, Windows 11
- Git branch: `main`
- Run: `python main.py` from project root
- API keys in `.env` (GROQ_API_KEY required, GEMINI_API_KEY unused)
