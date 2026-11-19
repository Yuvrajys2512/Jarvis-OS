# JARVIS OS

A local, voice-driven AI agent for your desktop. Say "Jarvis", give it a task, and it plans, uses tools on your computer, and talks back, while a full-screen HUD shows every step it takes.

## How it works

```
wake word ("Jarvis")  →  speech-to-text  →  orchestrator agent (tool-calling loop)  →  tools  →  text-to-speech
        faster-whisper       faster-whisper        Groq LLM                     system / browser     edge-tts
                                                     │
                                                     └─ ask_researcher → Researcher agent (owns the browser tools)
```

- **Multi-agent.** An orchestrator handles system actions and hands web research to a dedicated Researcher agent. Both share one reusable tool-calling loop (`core/agent_base.py`).
- **16 tools** across system control (open apps, run terminal commands, open your recent VS Code project), a visible Playwright-driven Chrome (search, open URLs, read pages, compare prices) and extras (weather, timers, clipboard, file search, screenshots and screen description).
- **Live HUD.** A FastAPI + WebSocket dashboard (`server.py`, `static/index.html`) changes state for idle / listening / thinking / speaking and narrates each tool call as it runs. When a tool opens an app, the HUD steps behind it and comes back on top when the tool finishes.
- **Mostly offline.** Wake word, transcription and speech run locally; only the LLM call goes to Groq.

## Run it

Windows is the main target (window management uses the Win32 API).

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env      # add your GROQ_API_KEY
python main.py
```

The dashboard opens at http://localhost:7777. Say "goodbye jarvis" to shut it down. `demo.py` runs a scripted demo, and `diagnose_mic.py` helps if the wake word isn't picking you up.

## Tests

```bash
pytest tests/
```
