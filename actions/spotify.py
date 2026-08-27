import time
import os
import urllib.parse
import subprocess
import pyautogui


# =========================================================
# OPEN SPOTIFY
# =========================================================

def open_spotify():

    try:

        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Spotify.exe"],
            capture_output=True,
            text=True
        )

        if "Spotify.exe" in result.stdout:

            print("🎵 Spotify is already running.")

            return True

    except Exception:
        pass

    try:

        os.startfile("spotify:")

        print("🎵 Opening Spotify...")

        time.sleep(3)

        return True

    except Exception as e:

        print(f"❌ Spotify open error: {e}")

        return False


# =========================================================
# PLAY
# =========================================================

def play_song(query):

    print(f"🎵 Spotify: playing '{query}'")

    if not open_spotify():

        return (
            False,
            "I couldn't open Spotify."
        )

    time.sleep(2)

    encoded_query = urllib.parse.quote(query)

    uri = f"spotify:search:{encoded_query}"

    print(f"🔎 Searching Spotify: {query}")

    try:

        os.startfile(uri)

    except Exception as e:

        print(f"❌ Spotify search error: {e}")

        return (
            False,
            "I couldn't search Spotify."
        )

    time.sleep(3)

    # -----------------------------------------------------
    # Current working position on your screen
    # -----------------------------------------------------

    SONG_X = -695
    SONG_Y = 244

    try:

        print(
            f"🖱️ Selecting first result "
            f"at ({SONG_X}, {SONG_Y})"
        )

        pyautogui.click(
            SONG_X,
            SONG_Y
        )

        time.sleep(1)

        return (
            True,
            f"Playing {query}."
        )

    except Exception as e:

        print(
            f"❌ Spotify playback error: {e}"
        )

        return (
            False,
            "I couldn't play that song."
        )


# =========================================================
# CONTROLS
# =========================================================

def control(command):

    command = command.lower().strip()

    try:

        if command in ["pause", "play", "resume"]:

            pyautogui.press("playpause")

            if command == "pause":
                return True, "Paused."

            return True, "Playing."

        if command in ["next", "next_song", "skip"]:

            pyautogui.press("nexttrack")

            return True, "Skipping to the next song."

        if command in ["previous", "previous_song", "back"]:

            pyautogui.press("prevtrack")

            return True, "Going back to the previous song."

        return (
            False,
            "I don't know that Spotify command."
        )

    except Exception as e:

        print(
            f"❌ Spotify control error: {e}"
        )

        return (
            False,
            "I couldn't control Spotify."
        )