import time

import sounddevice as sd
import numpy as np

from faster_whisper import WhisperModel
from speak import speak

from agent.core import run_agent


# =========================================================
# SETTINGS
# =========================================================

SAMPLE_RATE = 16000

# כמה זמן של שקט מסמן שסיימת לדבר
SILENCE_DURATION = 0.8

# כמה זמן לחכות לתחילת דיבור
MAX_WAIT = 10

# רגישות למיקרופון
SPEECH_THRESHOLD = 0.015


# =========================================================
# LOAD WHISPER
# =========================================================

print("🧠 Loading Jarvis...")

whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("✅ Jarvis ready!")
print("🎤 Speak to me...")
print()


# =========================================================
# VOLUME
# =========================================================

def volume(audio):
    """
    Calculates the RMS volume of an audio chunk.
    """

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
    Displays Jarvis's response and speaks it aloud.
    """

    if not text:
        return

    text = str(text).strip()

    if not text:
        return

    print(
        f"🤖 Jarvis: {text}"
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
    """
    Listen through the microphone until the user
    stops speaking.

    Returns:
        Transcribed English text.
    """

    print("🎤 Waiting for you...")

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

                    waited = (
                        time.time()
                        - start_time
                    )

                    if (
                        current_volume
                        > SPEECH_THRESHOLD
                    ):

                        speaking = True

                        print(
                            "🎤 Listening..."
                        )

                        audio_chunks.append(
                            audio
                        )

                    elif waited >= MAX_WAIT:

                        return ""

                # =================================================
                # USER IS SPEAKING
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

                    # User finished speaking
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
        "📝 Transcribing..."
    )

    # =========================================================
    # WHISPER
    # =========================================================

    try:

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

    except Exception as e:

        print(
            f"❌ Transcription error: {e}"
        )

        return ""


# =========================================================
# MAIN LOOP
# =========================================================

def main():

    print(
        "========================================"
    )

    print(
        "          Jarvis AI ASSISTANT"
    )

    print(
        "========================================"
    )

    print(
        "Agent mode: ON"
    )

    print(
        "Memory: ON"
    )

    print(
        "Tool calling: ON"
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
            f"👩 You: {text}"
        )

        # =====================================================
        # EXIT
        # =====================================================

        normalized = text.lower().strip()

        if normalized in [
            "exit",
            "quit",
            "goodbye",
            "stop"
        ]:

            respond(
                "Goodbye."
            )

            break

        # =====================================================
        # SEND TO AGENT
        # =====================================================

        try:

            print(
                "🧠 Sending request to Jarvis Agent..."
            )

            answer = run_agent(
                text
            )

        except KeyboardInterrupt:

            print()

            respond(
                "Goodbye."
            )

            break

        except Exception as e:

            print(
                f"❌ Agent error: {e}"
            )

            answer = (
                "I encountered an error "
                "while processing your request."
            )

        # =====================================================
        # RESPOND
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
        print("👋 Jarvis stopped.")

    except Exception as e:

        print(
            f"❌ Fatal error: {e}"
        )