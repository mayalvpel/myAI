import time

import sounddevice as sd
import numpy as np

from faster_whisper import WhisperModel

from agent.core_old import run_agent
from speak import speak


# =========================================================
# SETTINGS
# =========================================================

SAMPLE_RATE = 16000

SILENCE_DURATION = 0.8

MAX_WAIT = 10

SPEECH_THRESHOLD = 0.015

WHISPER_MODEL = "small"


# =========================================================
# SYSTEM
# =========================================================

print("🧠 טוענת את Nova / Jarvis...")

whisper = WhisperModel(
    WHISPER_MODEL,
    device="cpu",
    compute_type="int8"
)

print("✅ המערכת מוכנה!")
print("🎤 דברי אליי...")
print()


# =========================================================
# VOLUME
# =========================================================

def volume(audio):
    """
    Calculate RMS microphone volume.
    """

    return float(
        np.sqrt(
            np.mean(audio ** 2)
        )
    )


# =========================================================
# SPEAK
# =========================================================

def respond(text):
    """
    Print and speak the assistant response.
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

    print("🎤 מחכה שתדברי...")

    chunk_duration = 0.1

    chunk_size = int(
        SAMPLE_RATE * chunk_duration
    )

    audio_chunks = []

    speaking = False

    silence_time = 0

    start_time = time.time()

    try:

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

                current_volume = volume(
                    audio
                )

                # =================================================
                # WAITING FOR SPEECH
                # =================================================

                if not speaking:

                    waited_time = (
                        time.time()
                        - start_time
                    )

                    if (
                        current_volume
                        > SPEECH_THRESHOLD
                    ):

                        speaking = True

                        print(
                            "🎤 שומעת אותך..."
                        )

                        audio_chunks.append(
                            audio
                        )

                    elif (
                        waited_time
                        >= MAX_WAIT
                    ):

                        print(
                            "⏱️ לא זיהיתי דיבור."
                        )

                        return ""

                # =================================================
                # SPEAKING
                # =================================================

                else:

                    audio_chunks.append(
                        audio
                    )

                    if (
                        current_volume
                        < SPEECH_THRESHOLD
                    ):

                        silence_time += (
                            chunk_duration
                        )

                    else:

                        silence_time = 0

                    if (
                        silence_time
                        >= SILENCE_DURATION
                    ):

                        break

    except Exception as e:

        print(
            f"❌ Microphone error: {e}"
        )

        return ""

    # =========================================================
    # NO AUDIO
    # =========================================================

    if not audio_chunks:

        return ""

    # =========================================================
    # JOIN AUDIO
    # =========================================================

    audio = np.concatenate(
        audio_chunks
    )

    print(
        "📝 מתמללת..."
    )

    # =========================================================
    # WHISPER
    # =========================================================

    try:

        segments, info = whisper.transcribe(
            audio,
            language="he",
            beam_size=5,
            vad_filter=True
        )

        text = " ".join(
            segment.text
            for segment in segments
        ).strip()

        return text

    except Exception as e:

        print(
            f"❌ Whisper error: {e}"
        )

        return ""


# =========================================================
# EXIT
# =========================================================

EXIT_COMMANDS = {
    "יציאה",
    "לצאת",
    "להתראות",
    "סיימנו",
    "exit",
    "quit",
    "goodbye",
    "stop",
}


def is_exit_command(text):

    normalized = (
        str(text)
        .strip()
        .lower()
    )

    return normalized in EXIT_COMMANDS


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "========================================"
    )

    print(
        "             NOVA AI"
    )

    print(
        "========================================"
    )

    print(
        "🎤 Voice: ON"
    )

    print(
        "🧠 Agent: ON"
    )

    print(
        "🛠️ Tools: ON"
    )

    print(
        "💾 Memory: ON"
    )

    print()

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
            f"👩 את: {text}"
        )

        # =====================================================
        # EXIT
        # =====================================================

        if is_exit_command(text):

            respond(
                "להתראות ❤️"
            )

            break

        # =====================================================
        # AGENT
        # =====================================================

        try:

            print(
                "🧠 שולחת ל-Agent..."
            )

            answer = run_agent(
                text
            )

        except KeyboardInterrupt:

            print()

            respond(
                "להתראות ❤️"
            )

            break

        except Exception as e:

            print(
                f"❌ Agent error: {e}"
            )

            answer = (
                "מצטערת, נתקלתי בבעיה "
                "בעיבוד הבקשה."
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        respond(
            answer
        )

        print()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print("👋 Nova stopped.")

    except Exception as e:

        print(
            f"❌ Fatal error: {e}"
        )
