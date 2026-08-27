import time
import re

import ollama
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from speak import speak


# =========================
# הגדרות
# =========================

# MODEL = "aya-expanse:8b"
MODEL = "aya-expanse:8b-q2_K"

SAMPLE_RATE = 16000

SILENCE_DURATION = 0.8

MAX_WAIT = 10

SPEECH_THRESHOLD = 0.015


SYSTEM_PROMPT = """
את Nova, עוזרת קולית אישית.

עני תמיד בעברית בלבד.
עני ישירות על מה שהמשתמשת אמרה.
היי טבעית, נעימה וקצרה.
בשיחה קולית עני בדרך כלל במשפט אחד או שניים.

אל תציגי תהליך חשיבה.
אל תכתבי באנגלית.
אל תסבירי מה המשתמשת אמרה.
אל תכתבי "Okay" או "The user said".

אם לא הבנת את המשתמשת, אמרי:
"לא בטוחה שהבנתי, תוכלי לחזור על זה?"
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


print("✅ Nova מוכנה!")
print("🎤 דברי אליי...")
print()


# =========================
# עוצמת קול
# =========================

def volume(audio):

    return float(
        np.sqrt(
            np.mean(audio ** 2)
        )
    )


# =========================
# הקשבה
# =========================

def listen():

    print("🎤 מחכה שתדברי...")

    chunk_duration = 0.1
    chunk_size = int(
        SAMPLE_RATE * chunk_duration
    )

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

            audio, overflowed = stream.read(
                chunk_size
            )

            audio = np.squeeze(audio)

            current_volume = volume(audio)

            # =========================
            # מחכים לדיבור
            # =========================

            if not speaking:

                waited_time = (
                    time.time() - start_time
                )

                if current_volume > SPEECH_THRESHOLD:

                    speaking = True

                    print("🎤 שומעת אותך...")

                    audio_chunks.append(audio)

                elif waited_time >= MAX_WAIT:

                    print("⏱️ לא זיהיתי דיבור.")

                    return ""

            # =========================
            # בזמן דיבור
            # =========================

            else:

                audio_chunks.append(audio)

                if current_volume < SPEECH_THRESHOLD:

                    silence_time += chunk_duration

                else:

                    silence_time = 0

                if silence_time >= SILENCE_DURATION:

                    break


    # =========================
    # חיבור האודיו
    # =========================

    audio = np.concatenate(
        audio_chunks
    )

    print("📝 מתמללת...")

    segments, info = whisper.transcribe(
        audio,
        language="he",

        # חשוב לעברית
        initial_prompt=(
            "זוהי שיחה קולית בעברית. "
            "המשתמשת מדברת בעברית טבעית. "
            "מילים נפוצות: "
            "שלום, היי, מה שלומך, "
            "מה נשמע, תודה, בבקשה, "
            "כן, לא, אוקיי."
        ),

        beam_size=5,

        # עוזר למנוע טקסט הזוי
        condition_on_previous_text=False,

        # זיהוי אזורי דיבור
        vad_filter=True,
    )

    text = " ".join(
        segment.text
        for segment in segments
    ).strip()

    return text


# =========================
# ניקוי תשובת AI
# =========================

def clean_answer(answer):

    if not answer:
        return ""

    answer = answer.strip()

    # --------------------------------
    # אם יש </think>
    # קח רק מה שאחריו
    # --------------------------------

    if "</think>" in answer:

        answer = answer.split(
            "</think>",
            1
        )[1]

    # --------------------------------
    # אם נשאר <think>
    # --------------------------------

    if "<think>" in answer:

        answer = answer.split(
            "<think>",
            1
        )[0]

    # --------------------------------
    # ניקוי
    # --------------------------------

    answer = re.sub(
        r"\s+",
        " ",
        answer
    ).strip()

    return answer


# =========================
# Nova
# =========================

def ask_ai(text):

    start = time.time()

    print("🧠 חושבת...")

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        options={
            "num_ctx": 2048,
            "temperature": 0.3,
            "num_predict": 60
        }
    )

    answer = response.message.content.strip()

    ai_time = time.time() - start

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

    # =========================
    # יציאה
    # =========================

    if text.strip().lower() in [
        "יציאה",
        "לצאת",
        "להתראות",
        "סיימנו"
    ]:

        farewell = "להתראות!"

        print(
            f"🤖 Nova: {farewell}"
        )

        speak(farewell)

        break

    # =========================
    # AI
    # =========================

    answer = ask_ai(text)

    if not answer:

        answer = (
            "לא בטוחה שהבנתי, "
            "תוכלי לחזור על זה?"
        )

    print(
        f"🤖 Nova: {answer}"
    )

    # =========================
    # דיבור
    # =========================

    speak(answer)

    print()