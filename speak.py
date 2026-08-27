from pathlib import Path
import sys
import tempfile
import os
import wave
import winsound

from piper import PiperVoice


# =========================================================
# RESOURCE PATH
# =========================================================

def resource_path(relative_path):
    """
    Finds runtime files both when running normally
    and when running as a PyInstaller EXE.
    """

    relative_path = Path(relative_path)

    # -----------------------------------------------------
    # PyInstaller EXE
    # -----------------------------------------------------

    if getattr(sys, "frozen", False):

        # Folder containing Jarvis.exe
        base_path = Path(
            sys.executable
        ).resolve().parent

        path = (
            base_path
            / relative_path
        )

        if path.exists():
            return path

        # -------------------------------------------------
        # Fallback: PyInstaller internal directory
        # -------------------------------------------------

        internal_path = (
            base_path
            / "_internal"
            / relative_path
        )

        if internal_path.exists():
            return internal_path

        return path

    # -----------------------------------------------------
    # Normal Python execution
    # -----------------------------------------------------

    base_path = Path(
        __file__
    ).resolve().parent

    return (
        base_path
        / relative_path
    )


# =========================================================
# VOICE
# =========================================================

VOICE_PATH = resource_path(
    Path("en_GB")
    / "en_GB-alan-medium.onnx"
)


print(
    f"🔊 Loading Piper voice: {VOICE_PATH}"
)


if not VOICE_PATH.exists():

    raise FileNotFoundError(
        "Piper voice model not found:\n"
        f"{VOICE_PATH}"
    )


# =========================================================
# LOAD VOICE
# =========================================================

voice = PiperVoice.load(
    str(VOICE_PATH)
)


print(
    "✅ Piper voice ready!"
)


# =========================================================
# VOICE SETTINGS
# =========================================================

voice.config.length_scale = 0.78


# =========================================================
# SPEAK
# =========================================================

def speak(text):

    if not text:
        return

    text = str(
        text
    ).strip()

    if not text:
        return

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    )

    temp_path = temp_file.name

    temp_file.close()

    try:

        # -------------------------------------------------
        # Generate speech
        # -------------------------------------------------

        with wave.open(
            temp_path,
            "wb"
        ) as wav_file:

            voice.synthesize_wav(
                text,
                wav_file
            )

        # -------------------------------------------------
        # Play
        # -------------------------------------------------

        winsound.PlaySound(
            temp_path,
            winsound.SND_FILENAME
        )

    finally:

        try:

            os.remove(
                temp_path
            )

        except Exception:
            pass