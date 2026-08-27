from piper import PiperVoice
import wave

VOICE = r"C:\myAI\he_IL-saspeech-medium.onnx"

print("🔊 טוענת קול...")

voice = PiperVoice.load(VOICE)

# האטת קצב הדיבור
voice.config.length_scale = 1.5

print("🗣️ מייצרת דיבור...")

text = "שלום! אני נובה. עכשיו יש לי קול."

with wave.open("test_voice.wav", "wb") as wav_file:
    voice.synthesize_wav(text, wav_file)

print("✅ הקובץ נוצר: test_voice.wav")