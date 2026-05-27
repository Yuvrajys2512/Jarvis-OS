"""
Phase 3 verify — run this file, speak a sentence, see what Whisper heard.
Expected: your words printed to the terminal within a few seconds of stopping.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.speech_to_text import listen_and_transcribe

print("=== Speech-to-Text Test ===")
print("Speak after 'Listening...' appears. Stop talking and wait ~1.5s for it to finish.\n")

result = listen_and_transcribe()

print(f"\nJARVIS heard: \"{result}\"")
