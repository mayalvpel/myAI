import os
import time
import urllib.parse
import subprocess

import pyautogui

from actions.apps import open_app
from actions.youtube import search_youtube
from actions.web import search_web

from agent.memory import remember, recall

from agent.code_tools import (
    create_file,
    read_file,
    write_file,
    open_in_vscode,
    run_python,
    list_files,
)


# =========================================================
# APPLICATIONS
# =========================================================

def open_application(
    application: str
) -> str:
    """
    Open an application installed on Windows.
    """

    success, message, pending = open_app(
        application
    )

    if pending:

        return (
            f"INSTALL_CONFIRMATION_REQUIRED: {message}"
        )

    return message


# =========================================================
# YOUTUBE
# =========================================================

def youtube_search(
    query: str
) -> str:
    """
    Search YouTube for videos.
    """

    success, message = search_youtube(
        query
    )

    return message


# =========================================================
# WEB
# =========================================================

def web_search(
    query: str
) -> str:
    """
    Open a Google web search.
    """

    success, message = search_web(
        query
    )

    return message


# =========================================================
# SPOTIFY
# =========================================================

def open_spotify() -> bool:

    try:

        result = subprocess.run(
            [
                "tasklist",
                "/FI",
                "IMAGENAME eq Spotify.exe"
            ],
            capture_output=True,
            text=True
        )

        if "Spotify.exe" in result.stdout:

            print(
                "🎵 Spotify is already running."
            )

            return True

    except Exception:
        pass

    try:

        os.startfile(
            "spotify:"
        )

        print(
            "🎵 Opening Spotify..."
        )

        time.sleep(3)

        return True

    except Exception as e:

        print(
            f"❌ Spotify open error: {e}"
        )

        return False


def spotify_play(
    song: str
) -> str:
    """
    Open Spotify, search for a song,
    and select the first result.
    """

    if not song or not song.strip():

        return (
            "ERROR: No song was specified."
        )

    song = song.strip()

    print(
        f"🎵 Spotify: playing '{song}'"
    )

    if not open_spotify():

        return (
            "ERROR: I couldn't open Spotify."
        )

    time.sleep(2)

    encoded_song = urllib.parse.quote(
        song
    )

    spotify_uri = (
        f"spotify:search:{encoded_song}"
    )

    print(
        f"🔎 Searching Spotify: {song}"
    )

    try:

        os.startfile(
            spotify_uri
        )

    except Exception as e:

        print(
            f"❌ Spotify search error: {e}"
        )

        return (
            "ERROR: I couldn't search Spotify."
        )

    time.sleep(3)

    SONG_X = -695
    SONG_Y = 244

    try:

        print(
            f"🖱️ Selecting first Spotify result "
            f"at ({SONG_X}, {SONG_Y})"
        )

        pyautogui.click(
            SONG_X,
            SONG_Y
        )

        time.sleep(1)

        return (
            f"Playing {song}."
        )

    except Exception as e:

        print(
            f"❌ Spotify playback error: {e}"
        )

        return (
            "ERROR: I couldn't start Spotify playback."
        )


# =========================================================
# MEMORY
# =========================================================

def save_memory(
    content: str,
    category: str = "general"
) -> str:

    return remember(
        content,
        category
    )


def search_memory(
    query: str
) -> str:

    return recall(
        query
    )


# =========================================================
# CODE TOOLS
# =========================================================

def create_code_file(
    path: str,
    content: str
) -> str:
    """
    Create a new source-code file inside the JARVIS project.
    """

    return create_file(
        path=path,
        content=content
    )


def read_code_file(
    path: str
) -> str:
    """
    Read a source-code file inside the JARVIS project.
    """

    return read_file(
        path=path
    )


def write_code_file(
    path: str,
    content: str
) -> str:
    """
    Update or replace a source-code file.
    """

    return write_file(
        path=path,
        content=content
    )


def open_code_in_vscode(
    path: str = "."
) -> str:
    """
    Open a project file or directory in VS Code.
    """

    return open_in_vscode(
        path=path
    )


def run_python_file(
    path: str
) -> str:
    """
    Run a Python file inside the JARVIS project.
    """

    return run_python(
        path=path
    )


def list_project_files(
    path: str = "."
) -> str:
    """
    List files inside the JARVIS project.
    """

    return list_files(
        path=path
    )