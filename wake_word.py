import time

import numpy as np
import sounddevice as sd


# =========================================================
# SETTINGS
# =========================================================

SAMPLE_RATE = 16000

# כל כמה שניות נקליט קטע לבדיקה
CHUNK_DURATION = 1.5

CHUNK_SIZE = int(
    SAMPLE_RATE * CHUNK_DURATION
)

# כמה חזק צריך להיות הקול כדי שננסה לתמלל
SPEECH_THRESHOLD = 0.012

# זמן המתנה בין בדיקות
CHECK_INTERVAL = 0.05


# =========================================================
# JARVIS WAKE WORD
# =========================================================

class JarvisWakeWord:

    def __init__(
        self,
        whisper,
    ):
        """
        Wake-word detector based on the existing Whisper model.

        We intentionally do NOT use openWakeWord here.
        """

        self.whisper = whisper

        print(
            "🧠 Jarvis wake-word detector: Whisper mode"
        )

        print(
            "✅ Wake-word detector ready!"
        )

    # =====================================================
    # VOLUME
    # =====================================================

    @staticmethod
    def volume(audio):
        if audio is None:
            return 0.0

        if len(audio) == 0:
            return 0.0

        return float(
            np.sqrt(
                np.mean(
                    audio ** 2
                )
            )
        )

    # =====================================================
    # TRANSCRIBE
    # =====================================================

    def transcribe(
        self,
        audio,
    ):
        try:

            segments, info = (
                self.whisper.transcribe(
                    audio,
                    language="en",
                    beam_size=1,
                    vad_filter=True,
                )
            )

            text = " ".join(
                segment.text
                for segment in segments
            ).strip()

            return text

        except Exception as e:

            print(
                f"❌ Wake transcription error: {e}"
            )

            return ""

    # =====================================================
    # IS JARVIS
    # =====================================================

    @staticmethod
    def is_jarvis(text):

        if not text:
            return False

        normalized = (
            text
            .lower()
            .strip()
        )

        # Remove common punctuation
        for char in [
            ".",
            ",",
            "!",
            "?",
            ":",
            ";",
        ]:

            normalized = (
                normalized.replace(
                    char,
                    " ",
                )
            )

        words = normalized.split()

        if not words:
            return False

        # -------------------------------------------------
        # Exact / normal cases
        # -------------------------------------------------

        wake_phrases = [
            "jarvis",
            "hey jarvis",
            "hi jarvis",
            "okay jarvis",
            "ok jarvis",
            "hey jervis",
            "hi jervis",
            "jervis",
        ]

        if normalized in wake_phrases:
            return True

        # -------------------------------------------------
        # More tolerant detection
        #
        # Example:
        # "hey jarvis can you hear me"
        # -------------------------------------------------

        jarvis_variants = [
            "jarvis",
            "jervis",
        ]

        has_jarvis = any(
            word in jarvis_variants
            for word in words
        )

        if has_jarvis:
            return True

        return False

    # =====================================================
    # WAIT
    # =====================================================

    def wait(self):

        print(
            '👂 Waiting for "Hey Jarvis"...'
        )

        try:

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=CHUNK_SIZE,
            ) as stream:

                while True:

                    audio, overflowed = (
                        stream.read(
                            CHUNK_SIZE
                        )
                    )

                    audio = np.squeeze(
                        audio
                    )

                    # -----------------------------------------
                    # Ignore silence
                    # -----------------------------------------

                    current_volume = (
                        self.volume(
                            audio
                        )
                    )

                    if (
                        current_volume
                        < SPEECH_THRESHOLD
                    ):

                        time.sleep(
                            CHECK_INTERVAL
                        )

                        continue

                    # -----------------------------------------
                    # We heard speech
                    # -----------------------------------------

                    print(
                        "🎤 Checking wake phrase..."
                    )

                    text = self.transcribe(
                        audio
                    )

                    if not text:
                        continue

                    print(
                        f"🔎 Heard: {text}"
                    )

                    # -----------------------------------------
                    # Check for Jarvis
                    # -----------------------------------------

                    if self.is_jarvis(
                        text
                    ):

                        print(
                            "⚡ Jarvis detected!"
                        )

                        return True

        except KeyboardInterrupt:

            raise

        except Exception as e:

            print(
                f"❌ Wake-word microphone error: {e}"
            )

            time.sleep(
                1
            )

            return False

    # =====================================================
    # RESET
    # =====================================================

    def reset(self):
        """
        Nothing special is required for Whisper mode,
        but this method is kept so main.py can safely
        reset the detector after a session.
        """

        return