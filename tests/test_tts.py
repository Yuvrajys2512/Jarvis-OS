"""
Phase 2 verify — run this file to hear JARVIS speak.
Expected: audio plays through your speakers in ~2-3 seconds.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.text_to_speech import speak

print("Sending text to edge-tts... you should hear speech in a moment.")
speak("Good evening. I am JARVIS, your personal AI assistant. All systems are online and fully operational.")
print("Done. If you heard that, Phase 2 is complete.")
