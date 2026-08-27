import time

import ollama
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel


# =========================
# הגדרות
# =========================

MODEL = "qwen3:1.7b"

SAMPLE_RATE = 16000

# כמה זמן של שקט אומר שסיימת לדבר
SILENCE_DURATION = 0.8

# כמה זמן נחכה שתתחילי לדבר
MAX_WAIT = 10

# רגישות למיקרופון
# אם הוא לא מזהה אותך -> נעלה
# אם הוא מזהה רעשי רקע כדיבור -> נוריד
SPEECH_THRESHOLD = 0.015


SYSTEM_PROMPT = """
אתה Nova, העוזרת האישית שלי.

דברי איתי בעברית.
היי טבעית, נעימה וקצרה.
בשיחה קולית תני תשובות קצרות וברורות.
אל תסבירי את תהליך החשיבה שלך.
אל תכתבי Thinking.
אם השאלה פשוטה, עני במשפט או שניים.
"""


# =========================
# טעינת Whisper
# =========================

print("🧠 טוענת את Nova...")

whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


# =========================
# זיכרון השיחה
# =========================

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


print("✅ Nova מוכנה!")
print("🎤 דברי אליי...")
print()


# =========================
# חישוב עוצמת קול
# =========================

def volume(audio):
    """
    מחזיר את עוצמת האודיו.
    """

    return float(np.sqrt(np.mean(audio ** 2)))


# =========================
# הקלטה עם זיהוי דיבור
# =========================

def listen():

    print("🎤 מחכה שתדברי...")

    chunk_duration = 0.1
    chunk_size = int(SAMPLE_RATE * chunk_duration)

    audio_chunks = []

    speaking = False
    silence_time = 0
    waited_time = 0

    start_time = time.time()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=chunk_size
    ) as stream:

        while True:

            audio, overflowed = stream.read(chunk_size)

            audio = np.squeeze(audio)

            current_volume = volume(audio)

            # =========================
            # עדיין מחכים שתתחילי לדבר
            # =========================

            if not speaking:

                waited_time = time.time() - start_time

                if current_volume > SPEECH_THRESHOLD:

                    speaking = True

                    print("🎤 שומעת אותך...")

                    audio_chunks.append(audio)

                elif waited_time >= MAX_WAIT:

                    print("⏱️ לא זיהיתי דיבור.")

                    return ""

            # =========================
            # כבר מדברת
            # =========================

            else:

                audio_chunks.append(audio)

                if current_volume < SPEECH_THRESHOLD:

                    silence_time += chunk_duration

                else:

                    silence_time = 0

                # מספיק זמן של שקט = סיימת
                if silence_time >= SILENCE_DURATION:

                    break

    # =========================
    # חיבור כל הקטעים
    # =========================

    audio = np.concatenate(audio_chunks)

    print("📝 מתמללת...")

    segments, info = whisper.transcribe(
        audio,
        language="he",
        beam_size=5
    )

    text = " ".join(
        segment.text for segment in segments
    ).strip()

    return text


# =========================
# שליחה ל-Nova
# =========================

def ask_ai(text):

    start = time.time()

    messages.append({
        "role": "user",
        "content": text
    })

    print("🧠 חושבת...")

    response = ollama.chat(
        model=MODEL,
        messages=messages,
        think=False,
        options={
            "num_ctx": 2048,
            "temperature": 0.3,
            "num_predict": 100
        }
    )

    answer = response.message.content.strip()

    ai_time = time.time() - start

    messages.append({
        "role": "assistant",
        "content": answer
    })

    print(f"⏱️ זמן AI: {ai_time:.2f} שניות")

    return answer


# =========================
# לולאת השיחה
# =========================

while True:

    text = listen()

    if not text:

        print()
        continue

    print()
    print(f"👩 את: {text}")

    # פקודות יציאה
    if text.strip().lower() in [
        "יציאה",
        "לצאת",
        "להתראות",
        "סיימנו"
    ]:

        print("🤖 Nova: להתראות ❤️")
        break

    answer = ask_ai(text)

    print(f"🤖 Nova: {answer}")
    print()