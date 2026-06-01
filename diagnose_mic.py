import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

print("Loading model...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print("\n--- SAY 'JARVIS' NOW (recording 3 seconds) ---\n")
audio = sd.rec(int(16000 * 3), samplerate=16000, channels=1, dtype="float32")
sd.wait()

rms = float(np.sqrt(np.mean(audio ** 2)))
print(f"Mic volume (RMS): {rms:.4f}  {'<-- too quiet, check mic!' if rms < 0.003 else 'OK'}")

segs, _ = model.transcribe(audio.flatten(), language="en", beam_size=1, no_speech_threshold=0.1)
text = " ".join(s.text for s in segs)

print(f"Heard: [{text}]")
print(f"Would trigger: {any(w in text.lower() for w in ['jarvis','jarvi','jarves','jarvice','jarv'])}")
