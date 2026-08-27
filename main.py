import time

import sounddevice as sd
import numpy as np

from faster_whisper import WhisperModel
from speak import speak

from agent.core import run_agent
from wake_word import JarvisWakeWord


# =========================================================
# SETTINGS
# =========================================================

SAMPLE_RATE = 16000

# כמה זמן של שקט מסמן שסיימת לדבר
SILENCE_DURATION = 0.8

# כמה זמן לחכות לפקודה אחרי:
# "Yes, boss?"
COMMAND_TIMEOUT = 8

# רגישות למיקרופון
SPEECH_THRESHOLD = 0.015

# זמן לתת למיקרופון להירגע אחרי ש-Jarvis מדבר
WAKE_COOLDOWN = 1.2


# =========================================================
# LOAD WHISPER
# =========================================================

print(
    "🧠 Loading Whisper..."
)

whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
)

print(
    "✅ Whisper ready!"
)

print()


# =========================================================
# LOAD WAKE WORD
# =========================================================

wake_word = JarvisWakeWord(
    whisper
)

print()


# =========================================================
# VOLUME
# =========================================================

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


# =========================================================
# RESPOND
# =========================================================

def respond(text):

    if not text:
        return

    text = str(
        text
    ).strip()

    if not text:
        return

    print(
        f"🤖 Jarvis: {text}"
    )

    try:

        speak(
            text
        )

    except Exception as e:

        print(
            f"❌ Speech error: {e}"
        )

    # -----------------------------------------------------
    # Prevent microphone from immediately hearing TTS
    # -----------------------------------------------------

    time.sleep(
        WAKE_COOLDOWN
    )


# =========================================================
# LISTEN FOR COMMAND
# =========================================================

def listen(
    max_wait=COMMAND_TIMEOUT,
):

    print(
        "🎤 Listening..."
    )

    chunk_duration = 0.1

    chunk_size = int(
        SAMPLE_RATE
        * chunk_duration
    )

    audio_chunks = []

    speaking = False

    silence_time = 0.0

    start_time = time.time()

    try:

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:

            while True:

                audio, overflowed = (
                    stream.read(
                        chunk_size
                    )
                )

                audio = np.squeeze(
                    audio
                )

                current_volume = volume(
                    audio
                )

                # =================================================
                # WAIT FOR USER TO START SPEAKING
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

                        audio_chunks.append(
                            audio
                        )

                    elif (
                        waited
                        >= max_wait
                    ):

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

                        silence_time = 0.0

                    if (
                        silence_time
                        >= SILENCE_DURATION
                    ):

                        break

    except KeyboardInterrupt:

        raise

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

        segments, info = (
            whisper.transcribe(
                audio,
                language="en",
                beam_size=3,
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
            f"❌ Transcription error: {e}"
        )

        return ""


# =========================================================
# ACTIVE SESSION
# =========================================================

def active_session():

    """
    Jarvis is awake.

    He waits for a command.

    If the user says nothing for COMMAND_TIMEOUT
    seconds, the session ends and Jarvis returns
    to wake-word mode.
    """

    print()
    print(
        f"🎤 Listening for command "
        f"({COMMAND_TIMEOUT}s)..."
    )

    while True:

        # =====================================================
        # LISTEN
        # =====================================================

        text = listen(
            max_wait=COMMAND_TIMEOUT
        )

        # =====================================================
        # TIMEOUT
        # =====================================================

        if not text:

            print()

            respond(
                "Goodbye, boss."
            )

            return

        text = str(
            text
        ).strip()

        if not text:
            continue

        # =====================================================
        # USER
        # =====================================================

        print()

        print(
            f"👩 You: {text}"
        )

        normalized = (
            text
            .lower()
            .strip()
        )

        # =====================================================
        # SLEEP
        # =====================================================

        if normalized in [
            "exit",
            "quit",
            "goodbye",
            "stop",
            "bye",
            "sleep",
            "go to sleep",
        ]:

            respond(
                "Going back to sleep, boss."
            )

            return

        # =====================================================
        # AGENT
        # =====================================================

        try:

            print(
                "🧠 Sending request "
                "to Jarvis Agent..."
            )

            answer = run_agent(
                text
            )

        except KeyboardInterrupt:

            raise

        except Exception as e:

            print(
                f"❌ Agent error: {e}"
            )

            answer = (
                "I encountered an error "
                "while processing your request."
            )

        # =====================================================
        # RESPONSE
        # =====================================================

        respond(
            answer
        )

        print()

        print(
            f"🎤 Listening for another command "
            f"({COMMAND_TIMEOUT}s)..."
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "========================================"
    )

    print(
        "          JARVIS AI ASSISTANT"
    )

    print(
        "========================================"
    )

    print(
        "🟢 Jarvis is now running."
    )

    print(
        'Say "Hey Jarvis" to wake me.'
    )

    print()

    print(
        "Memory: ON"
    )

    print(
        "Tool calling: ON"
    )

    print(
        "Wake word: ON"
    )

    print()

    # =====================================================
    # PERMANENT LOOP
    # =====================================================

    # =========================================================
    # PERMANENT LOOP
    # =========================================================

    while True:

        try:

            # =================================================
            # SLEEPING / WAKE MODE
            # =================================================

            print(
                '👂 Waiting for "Hey Jarvis"...'
            )

            try:

                detected = wake_word.wait()

            except Exception as e:

                import traceback

                error_text = traceback.format_exc()

                print()
                print(
                    "❌ Wake-word error:"
                )
                print(
                    error_text
                )

                try:

                    from pathlib import Path

                    log_path = (
                        Path.cwd()
                        / "jarvis_wake_error.log"
                    )

                    log_path.write_text(
                        error_text,
                        encoding="utf-8",
                    )

                    print(
                        f"📄 Wake-word error saved to: "
                        f"{log_path}"
                    )

                except Exception:
                    pass

                time.sleep(2)

                continue

            # =================================================
            # NO DETECTION
            # =================================================

            if not detected:

                continue

            # =================================================
            # WAKE DETECTED
            # =================================================

            print()

            print(
                "⚡ Jarvis detected!"
            )

            # =================================================
            # RESET WAKE WORD
            # =================================================

            try:

                wake_word.reset()

            except Exception as e:

                print(
                    f"⚠️ Wake-word reset error: {e}"
                )

            # =================================================
            # WAKE RESPONSE
            # =================================================

            respond(
                "Yes, boss?"
            )

            # =================================================
            # ACTIVE SESSION
            # =================================================

            active_session()

            # =================================================
            # SESSION ENDED
            # =================================================

            print()

            print(
                "😴 Jarvis is going back to sleep..."
            )

            print()

            try:

                wake_word.reset()

            except Exception as e:

                print(
                    f"⚠️ Wake-word reset error: {e}"
                )

        # =====================================================
        # KEYBOARD INTERRUPT
        # =====================================================

        except KeyboardInterrupt:

            print()

            print(
                "👋 Jarvis stopped."
            )

            break

        # =====================================================
        # UNEXPECTED ERROR
        # =====================================================

        except Exception as e:

            import traceback

            error_text = traceback.format_exc()

            print()
            print(
                "❌ Main loop error:"
            )
            print(
                error_text
            )

            # -------------------------------------------------
            # Save crash log
            # -------------------------------------------------

            try:

                from pathlib import Path

                log_path = (
                    Path.cwd()
                    / "jarvis_error.log"
                )

                log_path.write_text(
                    error_text,
                    encoding="utf-8",
                )

                print(
                    f"📄 Error log saved to: "
                    f"{log_path}"
                )

            except Exception:
                pass

            print(
                "🔄 Restarting..."
            )

            time.sleep(2)

# =========================================================
# START
# =========================================================

# if __name__ == "__main__":

#     try:

#         main()

#     except KeyboardInterrupt:

#         print()

#         print(
#             "👋 Jarvis stopped."
#         )

#     except Exception as e:

#         print()

#         print(
#             f"❌ Fatal error: {e}"
#         )

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

        import traceback

        error_text = traceback.format_exc()

        print()
        print("❌ FATAL JARVIS ERROR")
        print("=" * 60)
        print(error_text)
        print("=" * 60)

        # Save error next to the EXE / working directory
        try:

            from pathlib import Path

            log_path = (
                Path.cwd()
                / "jarvis_error.log"
            )

            log_path.write_text(
                error_text,
                encoding="utf-8",
            )

            print()
            print(
                f"📄 Error log saved to:"
            )
            print(
                str(log_path)
            )

        except Exception as log_error:

            print(
                f"❌ Could not save error log: {log_error}"
            )

        print()
        print(
            "Jarvis crashed, but the window will stay open."
        )

        input(
            "\nPress ENTER to close..."
        )