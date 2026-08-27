import time
import os
import subprocess
import urllib.parse
import pyautogui


# =========================================================
# OPEN SPOTIFY
# =========================================================

def open_spotify():
    """
    Opens Spotify Desktop.
    """

    # Check if Spotify is already running
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

    # Open Spotify through its Windows URI
    try:
        os.startfile("spotify:")

        print("🎵 Opening Spotify...")

        time.sleep(3)

        return True

    except Exception as e:
        print(f"⚠️ Spotify URI error: {e}")

    # Fallback
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", "spotify:"],
            shell=False
        )

        print("🎵 Opening Spotify...")

        time.sleep(3)

        return True

    except Exception as e:
        print(f"❌ Could not open Spotify: {e}")

        return False


# =========================================================
# SEARCH SPOTIFY
# =========================================================

def search_spotify(query):
    """
    Opens Spotify directly on search results.
    """

    encoded_query = urllib.parse.quote(
        query
    )

    uri = f"spotify:search:{encoded_query}"

    print(f"🔎 Spotify URI: {uri}")

    try:
        os.startfile(uri)

        time.sleep(3)

        return True

    except Exception as e:

        print(
            f"❌ Spotify search error: {e}"
        )

        return False


# =========================================================
# PLAY SONG
# =========================================================

def play_song(query):

    print(f"🎵 Spotify: playing '{query}'")

    # פתיחת Spotify אם הוא לא פתוח
    if not open_spotify():
        return (
            False,
            "I couldn't open Spotify."
        )

    # יצירת Spotify search URI
    encoded_query = urllib.parse.quote(query)

    uri = f"spotify:search:{encoded_query}"

    print(f"🔎 Searching Spotify for: {query}")

    try:
        os.startfile(uri)
    except Exception as e:
        print(f"❌ Could not open Spotify search: {e}")

        return (
            False,
            "I couldn't search Spotify."
        )

    # לחכות לתוצאות
    time.sleep(3)

    try:

        # מיקום תוצאת החיפוש אצלך
        SONG_X = -695
        SONG_Y = 244

        print(
            f"🖱️ Clicking song at "
            f"({SONG_X}, {SONG_Y})"
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
            f"❌ Could not click song: {e}"
        )

        return (
            False,
            "I found the song but couldn't play it."
        )

# =========================================================
# PAUSE
# =========================================================

def pause():

    try:

        pyautogui.press(
            "playpause"
        )

        return (
            True,
            "Paused."
        )

    except Exception as e:

        print(
            f"❌ Spotify pause error: {e}"
        )

        return (
            False,
            "I couldn't pause Spotify."
        )


# =========================================================
# RESUME
# =========================================================

def resume():

    try:

        pyautogui.press(
            "playpause"
        )

        return (
            True,
            "Playing."
        )

    except Exception as e:

        print(
            f"❌ Spotify resume error: {e}"
        )

        return (
            False,
            "I couldn't resume Spotify."
        )


# =========================================================
# NEXT TRACK
# =========================================================

def next_track():

    try:

        pyautogui.press(
            "nexttrack"
        )

        return (
            True,
            "Skipping to the next song."
        )

    except Exception as e:

        print(
            f"❌ Spotify next error: {e}"
        )

        return (
            False,
            "I couldn't skip the song."
        )


# =========================================================
# PREVIOUS TRACK
# =========================================================

def previous_track():

    try:

        pyautogui.press(
            "prevtrack"
        )

        return (
            True,
            "Going to the previous song."
        )

    except Exception as e:

        print(
            f"❌ Spotify previous error: {e}"
        )

        return (
            False,
            "I couldn't go to the previous song."
        )


# =========================================================
# CURRENTLY PLAYING
# =========================================================

def currently_playing():

    return (
        False,
        "I can't read the currently playing song yet."
    )