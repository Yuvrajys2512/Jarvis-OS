"""
JARVIS — Local Agentic AI Assistant
Run this file to start JARVIS. Say 'Jarvis' to activate.
The dashboard opens automatically at http://localhost:7777
"""
import sys
import random
import server


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

            print(f"\nCommand: \"{command}\"")
            server.emit("user", text=command)

            # Shutdown phrase
            if any(w in command.lower() for w in ["goodbye jarvis", "jarvis sleep", "shut down", "exit"]):
                server.emit("status", value="idle")
                speak("Goodbye, sir. JARVIS signing off.")
                sys.exit(0)

            # Think
            server.emit("status", value="thinking")
            print("Thinking...")

            # Patch agent to emit tool events to dashboard
            _patch_agent_for_dashboard()

            response = process_instruction(command)

            # Speak
            server.emit("jarvis", text=response)
            server.emit("status", value="speaking")
            print(f"JARVIS: \"{response}\"\n")
            speak(response)

        except KeyboardInterrupt:
            speak("Shutting down. Goodbye, sir.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            server.emit("status", value="idle")
            speak("I encountered an error, sir. Standing by.")


_agent_patched = False

# Brief spoken narration before each tool runs
_NARRATIONS = {
    "open_application":   lambda a: f"Opening {a.get('name', 'that')}.",
    "search_google":      lambda a: f"Pulling up a search for {a.get('query', 'that')}.",
    "open_url":           lambda a: "Opening that in your browser.",
    "find_prices":        lambda a: f"Checking prices for {a.get('query', 'that')}.",
    "get_page_text":      lambda a: "Reading that page.",
    "get_weather":        lambda a: (f"Checking the weather in {a['location']}." if a.get('location') else "Checking the current weather."),
    "set_timer":          lambda a: f"Setting a timer for {a.get('seconds', 0)} seconds.",
    "cancel_timer":       lambda a: "Cancelling that timer.",
    "search_files":       lambda a: f"Searching your files for {a.get('name', 'that')}.",
    "write_clipboard":    lambda a: "Copying that to your clipboard.",
    "take_screenshot":    lambda a: "Taking a screenshot.",
    "describe_screen":    lambda a: "Let me take a look at your screen.",
    "run_terminal_command": lambda a: "Running that command.",
}


def _patch_agent_for_dashboard():
    """Monkey-patch the agent's tool executor to emit events and narrate each tool."""
    global _agent_patched
    if _agent_patched:
        return
    import core.agent as agent_module
    from core.text_to_speech import speak as _speak
    original = agent_module._execute_tool

    def patched(name, args):
        server.emit("tool", name=name, args=args)
        narration_fn = _NARRATIONS.get(name)
        if narration_fn:
            try:
                line = narration_fn(args)
                if line:
                    _speak(line)
            except Exception:
                pass
        return original(name, args)

    agent_module._execute_tool = patched
    _agent_patched = True


def main() -> None:
    preload_models()
    print("Starting dashboard at http://localhost:7777")
    server.launch()
    run()


if __name__ == "__main__":
    main()
