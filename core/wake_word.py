import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from config.settings import AUDIO_SAMPLE_RATE

# Step size: how much new audio we add per iteration.
# Window: how much audio we send to Whisper each time.
# The window slides forward by STEP each loop, so any word said at any point
# in time is fully captured within one window cycle.
STEP_DURATION = 0.5    # seconds of new audio recorded per loop
WINDOW_DURATION = 2.0  # seconds transcribed each time

# Every phonetic mishear of "Jarvis" that Whisper has ever produced.
# Add anything new you spot in the terminal "[wake] heard:" lines.
_TRIGGERS = {
    "jarvis", "jarvi", "jarvi's", "jarves", "jarvice", "jarvi s", "jarv",
    "jarvs", "jarvas", "jarbis", "jarvis,", "jarbus", "jarvos", "jarvius",
    "jarvish", "jarview", "jarvisc", "jarby", "harvey", "harvey's",
    "travis", "travis,", "ferris", "ferris,", "harris", "jervis",
    "marvis", "garvis", "barvis", "carvis", "darvis",
    "jar vis", "jar-vis", "j.a.r.v.i.s",
}

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        print("Loading wake word model...")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        print("Wake word model ready.")
    return _model


def wait_for_wake_word() -> None:
    """
    Block until the user says 'Jarvis'.

    Uses a sliding window: records STEP_DURATION seconds of new audio each loop,
    keeps a rolling WINDOW_DURATION buffer, and transcribes the full window.
    This means 'Jarvis' said at any point is always fully within one window —
    the old fixed-chunk approach split words at chunk boundaries and missed them.

    initial_prompt biases Whisper's decoder toward 'Jarvis', making it far more
    likely to transcribe it correctly even in non-native accents or noisy rooms.
    """
    model = _get_model()
    step_samples = int(AUDIO_SAMPLE_RATE * STEP_DURATION)
    window_samples = int(AUDIO_SAMPLE_RATE * WINDOW_DURATION)

    # Rolling audio buffer — always holds the last WINDOW_DURATION seconds
    buffer = np.zeros(window_samples, dtype="float32")

    print("Waiting for 'Jarvis'...")
    _silent_ticks = 0

    while True:
        # Record next step (blocks for STEP_DURATION seconds)
        chunk = sd.rec(step_samples, samplerate=AUDIO_SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        chunk = chunk.flatten()

        # Slide buffer: drop oldest step, append newest
        buffer = np.roll(buffer, -step_samples)
        buffer[-step_samples:] = chunk

        # Skip transcription if the buffer is near-silent (saves CPU)
        rms = float(np.sqrt(np.mean(buffer ** 2)))
        if rms < 0.0003:
            _silent_ticks += 1
            if _silent_ticks % 10 == 0:
                print(f"  [wake] no signal (RMS={rms:.5f}) — check mic", end="\r")
            continue
        _silent_ticks = 0
        print(f"  [wake] RMS={rms:.4f}", end="\r")

        segments, _ = model.transcribe(
            buffer,
            language="en",
            beam_size=5,                   # more search → more accurate than beam_size=1
            best_of=5,
            initial_prompt="Jarvis.",      # strongly biases decoder toward this word
            condition_on_previous_text=False,
            no_speech_threshold=0.6,       # standard threshold; don't discard borderline audio
            temperature=0.0,               # deterministic — no random sampling
        )
        text = " ".join(s.text for s in segments).lower().strip()

        if text:
            print(f"  [wake] heard: {text!r}")

        if any(trigger in text for trigger in _TRIGGERS):
            _play_activation_tone()
            return


def _play_activation_tone() -> None:
    """Two rising tones confirming JARVIS heard the wake word."""
    sample_rate = 22050
    duration = 0.12

    def make_tone(freq: float) -> np.ndarray:
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * freq * t).astype(np.float32)
        return tone * np.linspace(1.0, 0.0, len(tone)) * 0.4

    beep = np.concatenate([make_tone(880), make_tone(1320)])
    sd.play(beep, samplerate=sample_rate)
    sd.wait()
