"""
Phase 4 verify — full mini-loop: wake word → listen → echo back.
Expected:
  1. Terminal shows "Waiting for 'Jarvis'..."
  2. You say "Jarvis"
  3. A two-tone beep plays
  4. Terminal shows "Listening..."
  5. You speak a sentence
  6. JARVIS speaks your words back to you
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.wake_word import wait_for_wake_word
from core.speech_to_text import listen_and_transcribe
from core.text_to_speech import speak

print("=== Wake Word Test ===")
print("Say 'Jarvis' to activate, then speak any sentence.\n")

wait_for_wake_word()

print("Activated! Listening for your command...")
text = listen_and_transcribe()

print(f"You said: \"{text}\"")
speak(f"You said: {text}")
