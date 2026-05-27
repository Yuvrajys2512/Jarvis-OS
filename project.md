# JARVIS — Local Agentic AI Assistant

> A personal AI assistant that listens for your voice, understands complex multi-step instructions,
> controls your computer, sees through your webcam, automates your browser, and responds in a
> voice modeled after JARVIS from Iron Man. Runs entirely on your machine with zero ongoing API costs.

---

## What It Does

You say: *"Hey Jarvis, open my recent project, start the server, open localhost in the browser,
tell me what I'm wearing, then search Google for the cheapest mechanical keyboards."*

JARVIS:
1. Detects the wake word locally on your mic
2. Transcribes your full instruction
3. Sends it to an AI that breaks it into ordered tool calls
4. Executes each step — opens your IDE, runs a terminal command, launches the browser, captures
   your webcam and describes your outfit, navigates to Google, scrapes prices
5. Narrates everything it's doing in a calm, British-accented voice

---

## Tech Stack

| Layer | Tool | Why | Cost |
|---|---|---|---|
| Wake Word | OpenWakeWord | Open source, trainable, runs locally | Free |
| Speech-to-Text | faster-whisper | Offline Whisper, runs on CPU/GPU | Free |
| AI Brain | Google Gemini Flash | Free tier, tool use, vision, fast | Free |
| Text-to-Speech | edge-tts | Microsoft neural voices, offline capable | Free |
| Browser Automation | Playwright | Reliable, async, headless capable | Free |
| Vision | OpenCV + Gemini Vision | Webcam capture + AI description | Free |
| System Control | pyautogui + subprocess | Cross-platform keyboard/mouse/commands | Free |
| Language | Python 3.11+ | Best ecosystem for all of the above | Free |

---

## How the Pipeline Works (The Mental Model)

```
You speak
    ↓
[OpenWakeWord]  ← always listening, tiny CPU footprint
    ↓ "Hey Jarvis" detected
[faster-whisper]  ← records until silence, transcribes
    ↓ raw text instruction
[Gemini Flash]  ← acts as the brain, decides what tools to call and in what order
    ↓ sequence of tool calls
[Tool Executor]  ← runs each tool: open_app, run_command, search_web, see_webcam, etc.
    ↓ results from each tool
[Gemini Flash]  ← summarizes results into a natural response
    ↓ response text
[edge-tts]  ← converts to Jarvis-like speech
    ↓
You hear JARVIS speak
```

Every layer is independently testable. You can test STT without the brain, the brain without voice,
tools without the full pipeline. This is intentional — it makes debugging easy.

---

## Project Structure (what we will build)

```
JARVIS/
├── project.md              ← you are here
├── requirements.txt        ← all Python dependencies
├── .env.example            ← template for API keys
├── .env                    ← your actual keys (gitignored)
├── .gitignore
├── main.py                 ← entry point, starts the full loop
│
├── core/
│   ├── __init__.py
│   ├── wake_word.py        ← OpenWakeWord listener
│   ├── speech_to_text.py   ← faster-whisper transcription
│   ├── text_to_speech.py   ← edge-tts voice output
│   └── agent.py            ← Gemini Flash brain + tool orchestration
│
├── tools/
│   ├── __init__.py
│   ├── system.py           ← open apps, run terminal commands, file ops
│   ├── browser.py          ← Playwright: open URLs, search, scrape
│   └── vision.py           ← OpenCV webcam capture + Gemini vision
│
├── config/
│   ├── __init__.py
│   └── settings.py         ← paths, voice settings, model names
│
└── tests/
    ├── test_stt.py          ← test speech-to-text alone
    ├── test_tts.py          ← test voice output alone
    ├── test_tools.py        ← test each tool alone
    └── test_agent.py        ← test brain with mock tools
```

---

## Implementation Plan

Each phase ends with a **verified output** — something you can see, hear, or confirm with your own
eyes before moving to the next phase. We do not move forward until the verify step passes.

---

### Phase 1 — Project Scaffold & Environment

Getting the skeleton in place before any real code.

- [ ] 1.1 Create the full folder structure
- [ ] 1.2 Create `requirements.txt` with all dependencies listed
- [ ] 1.3 Create `.env.example` with placeholder keys
- [ ] 1.4 Create `.gitignore` (ignore `.env`, `__pycache__`, model cache files)
- [ ] 1.5 Create empty `__init__.py` files in each package folder
- [ ] 1.6 Create `config/settings.py` with basic config constants
- [ ] 1.7 Install all dependencies (`pip install -r requirements.txt`)
- [ ] 1.8 Initialize git repo and push to GitHub

**Verified Output:** `git status` is clean, repo is on GitHub, `pip install` completes with no errors.

---

### Phase 2 — Text-to-Speech (Jarvis Speaks)

We start with voice *output* not input, because hearing Jarvis respond is motivating and
it lets you test responses before the full pipeline exists.

- [ ] 2.1 Implement `core/text_to_speech.py` — wrap edge-tts, choose the voice
- [ ] 2.2 Write a quick test: pass a string, hear it spoken
- [ ] 2.3 Tune the voice settings (speed, pitch) to feel Jarvis-like
- [ ] 2.4 Make `speak()` async-safe so it doesn't block the main loop

**Verified Output:** Running `python -c "from core.text_to_speech import speak; speak('Good evening. All systems are online.')"` plays audio in the Jarvis voice.

---

### Phase 3 — Speech-to-Text (Jarvis Listens)

Getting your words into text reliably.

- [ ] 3.1 Implement `core/speech_to_text.py` — load faster-whisper model
- [ ] 3.2 Record from mic until silence is detected (voice activity detection)
- [ ] 3.3 Transcribe the recorded audio and return text
- [ ] 3.4 Write `tests/test_stt.py` — speak a sentence, print what it heard

**Verified Output:** You speak "open my browser and search for Python tutorials", the terminal prints exactly that back.

---

### Phase 4 — Wake Word Detection

JARVIS should only activate when you say "Hey Jarvis", not listen to everything all the time.

- [ ] 4.1 Implement `core/wake_word.py` using OpenWakeWord
- [ ] 4.2 Run it in a background thread that unblocks when triggered
- [ ] 4.3 Connect it to STT: wake word → start recording → transcribe
- [ ] 4.4 Add a small audio cue (beep or "Yes?" response) when wake word fires

**Verified Output:** You say "Hey Jarvis" → you hear a response tone → you speak → terminal prints your transcription.

---

### Phase 5 — System Tools (Jarvis Controls Your PC)

The hands of JARVIS.

- [ ] 5.1 Implement `tools/system.py`:
  - `open_application(name)` — opens Notepad, VS Code, etc. by name
  - `run_terminal_command(command)` — runs shell commands, returns output
  - `get_recent_project()` — reads recent VS Code projects from settings
- [ ] 5.2 Write `tests/test_tools.py` — call each function directly, verify behavior
- [ ] 5.3 Add safety check: dangerous commands (rm -rf, format, etc.) require confirmation

**Verified Output:** Calling `open_application("notepad")` opens Notepad. Calling `run_terminal_command("echo hello")` returns `"hello"`.

---

### Phase 6 — Browser Tools (Jarvis Searches the Web)

- [ ] 6.1 Implement `tools/browser.py` using Playwright:
  - `open_url(url)` — opens a URL in the default browser
  - `search_google(query)` — navigates to Google, types the query, hits enter
  - `get_page_text(url)` — fetches visible text from a page (for price scraping)
  - `find_prices(query)` — searches and extracts price information
- [ ] 6.2 Install Playwright browsers (`playwright install chromium`)
- [ ] 6.3 Write tests for each browser function

**Verified Output:** Calling `search_google("cheapest mechanical keyboards")` opens a browser and shows results. `find_prices(...)` returns a list of products with prices.

---

### Phase 7 — Vision (Jarvis Sees You)

- [ ] 7.1 Implement `tools/vision.py`:
  - `capture_webcam_frame()` — takes a photo from your webcam using OpenCV
  - `describe_image(frame)` — sends frame to Gemini Vision, returns description
  - `what_am_i_wearing()` — combines both with a focused prompt
- [ ] 7.2 Test webcam capture (save a frame to disk, confirm it looks right)
- [ ] 7.3 Test Gemini vision description on a captured frame

**Verified Output:** Running the vision module captures your webcam and Gemini returns a description like *"You appear to be wearing a dark navy hoodie and glasses."*

---

### Phase 8 — The AI Brain (Gemini Flash + Tool Orchestration)

This is where everything connects. The brain receives your instruction and decides which tools
to call, in what order, with what arguments.

- [ ] 8.1 Set up Gemini Flash with the Google AI Python SDK
- [ ] 8.2 Define all tools as Gemini function declarations (name, description, parameters)
- [ ] 8.3 Implement `core/agent.py` — the main agent loop:
  - Sends user instruction + tool definitions to Gemini
  - Receives tool call decisions from Gemini
  - Executes each tool call
  - Feeds results back to Gemini
  - Gets final natural language response
- [ ] 8.4 Write `tests/test_agent.py` — send a text instruction, verify tool calls happen

**Verified Output:** Sending `"open notepad and tell me what 2 + 2 is"` causes Notepad to open AND Gemini returns a spoken answer — all from a text string, no voice yet.

---

### Phase 9 — Full Pipeline Integration

Connect every phase into the single loop.

- [ ] 9.1 Wire `main.py`: wake word → STT → agent → TTS
- [ ] 9.2 Handle errors gracefully (tool fails, mic not found, API rate limit)
- [ ] 9.3 Add logging so you can see what JARVIS is "thinking" in the terminal
- [ ] 9.4 Test the full demo scenario end-to-end

**Verified Output:** You say *"Hey Jarvis, open Notepad, then tell me what I'm wearing"* — Notepad opens and JARVIS speaks a description of your outfit in the Jarvis voice.

---

### Phase 10 — Polish & Personality

- [ ] 10.1 Write a Jarvis-style system prompt (formal, precise, slightly dry British humor)
- [ ] 10.2 Add startup sequence: JARVIS announces itself when `main.py` starts
- [ ] 10.3 Add a shutdown phrase: "Goodbye Jarvis" / "Jarvis sleep"
- [ ] 10.4 Create a simple config file so you can change voice/model without touching code
- [ ] 10.5 Final GitHub push with clean commit history

**Verified Output:** Running `python main.py` triggers a startup message. The full demo scenario from the project concept works end-to-end.

---

## API Keys You Will Need

| Key | Where to Get | Free? |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com | Yes, free tier |

That's the only external API. Everything else is local.

---

## Current Status

**Phase 1 — Complete**
**Phase 2 — Complete**
**Phase 3 — Complete**
**Phase 4 — Complete**
