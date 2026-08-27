import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
RECORD_SECONDS = 5

print("טוען את מודל Whisper...")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("המודל מוכן!")
print()
print(f"דברי במשך {RECORD_SECONDS} שניות...")

audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="float32"
)

sd.wait()

audio = np.squeeze(audio)

print("מתמלל...")

segments, info = model.transcribe(
    audio,
    language="he",
    beam_size=5
)

text = " ".join(segment.text for segment in segments)

print()
print("🎤 שמעתי:")
print(text)