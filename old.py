import time
import json
import re

import ollama
import sounddevice as sd
import numpy as np

from faster_whisper import WhisperModel
from speak import speak

from actions.router import execute_action

from actions.router import execute_action
from wake_word import wait_for_wake_word

# =========================================================
# SETTINGS
# =========================================================

MODEL = "qwen3:1.7b"

SAMPLE_RATE = 16000

# כמה זמן של שקט מסמן שסיימת לדבר
SILENCE_DURATION = 0.8

# כמה זמן לחכות לתחילת דיבור
MAX_WAIT = 10

# רגישות למיקרופון
SPEECH_THRESHOLD = 0.015

# פעולה שמחכה לאישור המשתמש
pending_action = None


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
PERSONALITY:

You are Nova, an elegant and highly capable AI assistant inspired by a sophisticated
futuristic personal assistant.

Speak calmly, confidently, intelligently, and professionally.

Your responses should be concise and polished.

Avoid overly enthusiastic language.
Avoid emojis.
Avoid phrases like "Sure!", "Absolutely!", "Of course!" unless appropriate.

Use natural British-style formal English when possible.

Examples:

Instead of:
"Sure! I'd be happy to help you with that!"

Say:
"Certainly. I'll take care of that."

Instead of:
"Oops, I couldn't open it!"

Say:
"I was unable to open the application."

Instead of:
"Okay, I'll do that!"

Say:
"Understood."

Instead of:
"Great! Spotify is now playing!"

Say:
"Spotify is now playing."

You should sound like a calm, intelligent, sophisticated AI assistant.

You MUST return ONLY valid JSON.

Never return markdown.
Never return explanations.
Never return thinking.
Never return English prose outside the JSON.

Available actions:

1. Open an application:

{
    "action": "open_app",
    "target": "calculator"
}

2. Play a Spotify song:

{
    "action": "spotify_play",
    "target": "Blinding Lights"
}

3. Control Spotify:

{
    "action": "spotify_control",
    "target": "pause"
}

Possible Spotify commands:

pause
resume
next
previous

4. Normal conversation:

{
    "action": "chat",
    "response": "Hello! How can I help?"
}

5. Search YouTube:

{
    "action": "youtube_search",
    "target": "Python tutorials"
}

6. Search the web:

{
    "action": "web_search",
    "target": "Python tutorials for beginners"
}

7. Install an application:

{
    "action": "install_app",
    "target": "spotify"
}

IMPORTANT RULES:

If the user asks to OPEN an application:
use "open_app".

Do NOT use "install_app" just because the application might not exist.

If the user explicitly asks to INSTALL an application:
use "install_app".

Examples:

User:
"hello"

Return:
{"action":"chat","response":"Hello! How can I help?"}

User:
"what's up?"

Return:
{"action":"chat","response":"I'm doing great! How can I help?"}

User:
"open calculator"

Return:
{"action":"open_app","target":"calculator"}

User:
"open WhatsApp"

Return:
{"action":"open_app","target":"whatsapp"}

User:
"open Spotify"

Return:
{"action":"open_app","target":"spotify"}

User:
"play Blinding Lights"

Return:
{"action":"spotify_play","target":"Blinding Lights"}

User:
"pause the music"

Return:
{"action":"spotify_control","target":"pause"}

User:
"next song"

Return:
{"action":"spotify_control","target":"next"}

User:
"search YouTube for Python tutorials"

Return:
{"action":"youtube_search","target":"Python tutorials"}

User:
"find Python tutorials on YouTube"

Return:
{"action":"youtube_search","target":"Python tutorials"}

User:
"search Google for Python tutorials"

Return:
{"action":"web_search","target":"Python tutorials"}

User:
"install Spotify"

Return:
{"action":"install_app","target":"spotify"}

Always return exactly ONE JSON object.
"""


# =========================================================
# LOAD WHISPER
# =========================================================

print("🧠 Loading Nova...")

whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("✅ Nova ready!")
print("🎤 Speak to me...")
print()


# =========================================================
# VOLUME
# =========================================================

def volume(audio):

    return float(
        np.sqrt(
            np.mean(audio ** 2)
        )
    )


# =========================================================
# SPEAK / RESPOND
# =========================================================

def respond(text):

    """
    מדפיס את התשובה של Nova
    ומשמיע אותה בקול.

    חשוב:
    הפונקציה הזו מקבלת רק תשובות של Nova,
    לא את מה שהמשתמש אמר.
    """

    if not text:
        return

    text = str(text).strip()

    if not text:
        return

    print(
        f"🤖 Nova: {text}"
    )

    try:

        speak(text)

    except Exception as e:

        print(
            f"❌ Speech error: {e}"
        )


# =========================================================
# LISTEN
# =========================================================

def listen():

    print("🎤 Waiting for you...")

    chunk_duration = 0.1

    chunk_size = int(
        SAMPLE_RATE * chunk_duration
    )

    audio_chunks = []

    speaking = False

    silence_time = 0

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

            # -------------------------------------------------
            # WAITING FOR SPEECH
            # -------------------------------------------------

            if not speaking:

                waited = (
                    time.time() - start_time
                )

                if current_volume > SPEECH_THRESHOLD:

                    speaking = True

                    print(
                        "🎤 Listening..."
                    )

                    audio_chunks.append(audio)

                elif waited >= MAX_WAIT:

                    return ""

            # -------------------------------------------------
            # USER IS SPEAKING
            # -------------------------------------------------

            else:

                audio_chunks.append(audio)

                if current_volume < SPEECH_THRESHOLD:

                    silence_time += chunk_duration

                else:

                    silence_time = 0

                # המשתמש סיים לדבר
                if silence_time >= SILENCE_DURATION:

                    break

    if not audio_chunks:

        return ""

    # ---------------------------------------------------------
    # JOIN AUDIO
    # ---------------------------------------------------------

    audio = np.concatenate(
        audio_chunks
    )

    print(
        "📝 Transcribing..."
    )

    # ---------------------------------------------------------
    # WHISPER
    # ---------------------------------------------------------

    segments, info = whisper.transcribe(
        audio,
        language="en",
        beam_size=3,
        vad_filter=True
    )

    text = " ".join(
        segment.text
        for segment in segments
    ).strip()

    return text


# =========================================================
# ASK AI
# =========================================================

def ask_ai(text):

    start = time.time()

    print(
        "🧠 Thinking..."
    )

    try:

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

            think=False,

            options={
                "num_ctx": 2048,
                "temperature": 0.1,
                "num_predict": 100
            }
        )

        raw = response.message.content.strip()

    except Exception as e:

        print(
            f"❌ Ollama error: {e}"
        )

        return {
            "action": "chat",
            "response": "Sorry, I couldn't process that."
        }

    elapsed = time.time() - start

    print(
        f"⏱️ AI time: {elapsed:.2f} seconds"
    )

    print(
        f"🧠 Raw AI: {raw}"
    )

    # =====================================================
    # REMOVE THINKING
    # =====================================================

    if "<think>" in raw:

        if "</think>" in raw:

            raw = raw.split(
                "</think>",
                1
            )[1]

        else:

            raw = raw.split(
                "<think>",
                1
            )[0]

    raw = raw.strip()

    # =====================================================
    # REMOVE MARKDOWN CODE FENCES
    # =====================================================

    raw = raw.replace(
        "```json",
        ""
    )

    raw = raw.replace(
        "```",
        ""
    )

    raw = raw.strip()

    # =====================================================
    # PARSE JSON
    # =====================================================

    try:

        data = json.loads(
            raw
        )

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "AI returned JSON that isn't an object."
            )

        return data

    except Exception as e:

        print(
            f"⚠️ Invalid AI JSON: {e}"
        )

        print(
            f"⚠️ Received: {raw}"
        )

        return {
            "action": "chat",
            "response": "Sorry, I didn't understand that."
        }


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    # =====================================================
    # LISTEN
    # =====================================================

    text = listen()

    if not text:

        print()

        continue

    print()

    print(
        f"👩 You: {text}"
    )

    # =====================================================
    # EXIT
    # =====================================================

    if text.lower().strip() in [
        "exit",
        "quit",
        "goodbye",
        "stop"
    ]:

        respond(
            "Goodbye!"
        )

        break

    # =====================================================
    # HANDLE PENDING CONFIRMATION
    # =====================================================

    if pending_action is not None:

        normalized = text.lower().strip()

        # Remove punctuation Whisper may add
        normalized = re.sub(
            r"[.!?,;:'\"]",
            "",
            normalized
        ).strip()

        yes_words = [
            "yes",
            "yeah",
            "yep",
            "yup",
            "sure",
            "okay",
            "ok",
            "please",
            "do it",
            "go ahead",
            "install it",
            "install",
            "yes please",
            "sure please"
        ]

        no_words = [
            "no",
            "nope",
            "nah",
            "cancel",
            "don't",
            "do not",
            "no thanks",
            "never mind"
        ]

        # -------------------------------------------------
        # YES
        # -------------------------------------------------

        if normalized in yes_words:

            action_data = {
                "action": "install_app",
                "target": pending_action["target"]
            }

            if pending_action.get(
                "winget"
            ):

                action_data["winget"] = (
                    pending_action["winget"]
                )

            pending_action = None

            print(
                "✅ Confirmation received."
            )

            try:

                result = execute_action(
                    action_data
                )

                if not isinstance(
                    result,
                    tuple
                ):

                    success = False
                    answer = (
                        "I couldn't complete "
                        "the installation."
                    )
                    new_pending = None

                elif len(result) == 3:

                    success, answer, new_pending = result

                elif len(result) == 2:

                    success, answer = result
                    new_pending = None

                else:

                    success = False
                    answer = (
                        "I couldn't complete "
                        "the installation."
                    )
                    new_pending = None

            except Exception as e:

                print(
                    f"❌ Action error: {e}"
                )

                success = False

                answer = (
                    "I couldn't complete "
                    "the installation."
                )

                new_pending = None

            # -------------------------------------------------
            # INSTALL SUCCESS
            # -------------------------------------------------

            if success:

                respond(
                    answer
                )

                # -------------------------------------------------
                # TRY TO OPEN AFTER INSTALL
                # -------------------------------------------------

                target = action_data[
                    "target"
                ]

                print(
                    f"🚀 Opening {target}..."
                )

                try:

                    open_result = execute_action(
                        {
                            "action": "open_app",
                            "target": target
                        }
                    )

                    if (
                        isinstance(
                            open_result,
                            tuple
                        )
                        and len(open_result) >= 2
                    ):

                        open_success = (
                            open_result[0]
                        )

                        open_message = (
                            open_result[1]
                        )

                        if open_success:

                            respond(
                                open_message
                            )

                except Exception as e:

                    print(
                        f"⚠️ Could not open after install: {e}"
                    )

            else:

                respond(
                    answer
                )

            print()

            continue

        # -------------------------------------------------
        # NO
        # -------------------------------------------------

        elif normalized in no_words:

            pending_action = None

            respond(
                "Okay, I won't install it."
            )

            print()

            continue

        # -------------------------------------------------
        # NOT YES / NO
        # -------------------------------------------------

        else:

            respond(
                "Please say yes if you want me to install it, "
                "or no to cancel."
            )

            print()

            continue

    # =====================================================
    # NORMAL AI ACTION
    # =====================================================

    action_data = ask_ai(
        text
    )

    print(
        f"🧠 Raw action: {action_data}"
    )

    # =====================================================
    # EXECUTE ACTION
    # =====================================================

    try:

        result = execute_action(
            action_data
        )

    except Exception as e:

        print(
            f"❌ Action error: {e}"
        )

        respond(
            "Sorry, I couldn't perform that action."
        )

        print()

        continue

    # =====================================================
    # HANDLE RESULT
    # =====================================================

    if not isinstance(
        result,
        tuple
    ):

        success = False

        answer = (
            "I couldn't perform that action."
        )

        new_pending = None

    elif len(result) == 3:

        success, answer, new_pending = result

    elif len(result) == 2:

        success, answer = result

        new_pending = None

    else:

        success = False

        answer = (
            "I couldn't perform that action."
        )

        new_pending = None

    # =====================================================
    # SAVE PENDING INSTALLATION
    # =====================================================

    if new_pending is not None:

        pending_action = {
            "action": "install_app",
            "target": new_pending["target"],
            "winget": new_pending.get(
                "winget"
            )
        }

    # =====================================================
    # OUTPUT
    # =====================================================

    respond(
        answer
    )

    print()