"""
Phase 8 verify — test the AI brain with text instructions (no voice needed).
Watch the [tool] lines to see Gemini deciding what to call.
Expected: Notepad opens AND Gemini returns a spoken Jarvis-style response.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.agent import process_instruction
from core.text_to_speech import speak

print("=== Agent Brain Test ===\n")
print("Sending instruction to JARVIS brain...\n")

instruction = "Open Notepad and then tell me what 2 plus 2 is."

print(f"Instruction: \"{instruction}\"")
print("─" * 50)

response = process_instruction(instruction)

print("─" * 50)
print(f"\nJARVIS response: \"{response}\"")
print("\nSpeaking response...")
speak(response)
print("Done.")
