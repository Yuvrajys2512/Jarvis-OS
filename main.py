"""
JARVIS — Local Agentic AI Assistant
Run this file to start JARVIS. Say 'Jarvis' to activate.
"""
import sys


def preload_models() -> None:
    """Load all models into memory at startup so there's no delay mid-conversation."""
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

    speak("Good evening. JARVIS is online. How can I assist you?")

    while True:
        try:
            # Phase 1: wait for wake word
            wait_for_wake_word()

            # Phase 2: listen for command
            speak("Yes?")
            command = listen_and_transcribe()

            if not command.strip():
                speak("I didn't catch that, sir. Please try again.")
                continue

            print(f"\nCommand: \"{command}\"")

            # Check for shutdown phrase
            if any(word in command.lower() for word in ["goodbye jarvis", "jarvis sleep", "shut down", "exit"]):
                speak("Goodbye, sir. JARVIS signing off.")
                sys.exit(0)

            # Phase 3: process with AI brain
            print("Thinking...")
            response = process_instruction(command)

            # Phase 4: speak the response
            print(f"JARVIS: \"{response}\"\n")
            speak(response)

        except KeyboardInterrupt:
            speak("Shutting down. Goodbye, sir.")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            speak("I encountered an error, sir. Standing by.")


def main() -> None:
    preload_models()
    run()


if __name__ == "__main__":
    main()
