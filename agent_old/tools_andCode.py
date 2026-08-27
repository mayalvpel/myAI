import os
import time
import urllib.parse
import subprocess

import pyautogui

from actions.apps import (
    open_app,
    install_app,
)

from actions.youtube import search_youtube
from actions.web import search_web

from agent.memory import (
    remember,
    recall
)

from agent.code_tools import (
    create_file,
    read_file,
    write_file,
    open_in_vscode,
    run_python,
    list_files,
)

from actions.dependencies import (
    install_python_package,
)


# =========================================================
# APPLICATIONS
# =========================================================

def install_python_package_tool(
    package: str
) -> str:

    if not package:

        return (
            "ERROR: No Python package specified."
        )

    return install_python_package(
        package
    )


# =========================================================
# OPEN APPLICATION
# =========================================================

def open_application(
    application: str
) -> str:

    if not application:

        return (
            "ERROR: No application specified."
        )

    try:

        success, message, pending = open_app(
            application
        )

        # =================================================
        # INSTALLATION REQUIRED
        # =================================================

        if pending:

            winget_id = pending.get(
                "winget",
                ""
            )

            display_name = pending.get(
                "display_name",
                application
            )

            return (
                "INSTALL_CONFIRMATION_REQUIRED\n"
                f"APPLICATION: {application}\n"
                f"DISPLAY_NAME: {display_name}\n"
                f"WINGET_ID: {winget_id}\n"
                f"MESSAGE: {message}\n"
                "ACTION_REQUIRED: "
                "Ask the user whether they want to install "
                "the application. "
                "STOP processing the current request. "
                "Do not generate Python code. "
                "Do not claim the application was opened."
            )

        # =================================================
        # OPEN FAILED
        # =================================================

        if not success:

            return (
                "ERROR: "
                + str(message)
            )

        return str(message)

    except Exception as e:

        return (
            "ERROR: Could not open application: "
            f"{e}"
        )


# =========================================================
# INSTALL APPLICATION
# =========================================================

def install_application(
    application: str,
    winget_id: str = ""
) -> str:

    if not application:

        return (
            "ERROR: No application specified."
        )

    try:

        print(
            f"📦 Installing application: "
            f"{application}"
        )

        success, message, app_info = install_app(
            application,
            winget_id=winget_id or None
        )

        if not success:

            return (
                "ERROR: "
                + str(message)
            )

        # =================================================
        # NOW OPEN THE APPLICATION
        # =================================================

        print(
            f"🚀 Opening {application}..."
        )

        open_success, open_message, pending = open_app(
            application
        )

        if pending:

            # This should normally not happen because
            # installation just succeeded, but handle it.
            return (
                "INSTALL_SUCCESS_OPEN_PENDING: "
                f"{message} "
                f"{open_message}"
            )

        if not open_success:

            return (
                "INSTALL_SUCCESS_OPEN_FAILED: "
                f"{message} "
                f"However, I couldn't open "
                f"{application}: "
                f"{open_message}"
            )

        return (
            f"{message} "
            f"{open_message}"
        )

    except Exception as e:

        return (
            "ERROR: Could not install application: "
            f"{e}"
        )


# =========================================================
# YOUTUBE
# =========================================================

def youtube_search(
    query: str
) -> str:

    if not query:

        return (
            "ERROR: No YouTube query specified."
        )

    try:

        success, message = search_youtube(
            query
        )

        return str(message)

    except Exception as e:

        return (
            "ERROR: YouTube search failed: "
            f"{e}"
        )


# =========================================================
# WEB
# =========================================================

def web_search(
    query: str
) -> str:

    if not query:

        return (
            "ERROR: No web query specified."
        )

    try:

        success, message = search_web(
            query
        )

        return str(message)

    except Exception as e:

        return (
            "ERROR: Web search failed: "
            f"{e}"
        )


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
            text=True,
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

    try:

        os.startfile(
            spotify_uri
        )

    except Exception as e:

        return (
            "ERROR: I couldn't search Spotify: "
            f"{e}"
        )

    time.sleep(3)

    SONG_X = -695
    SONG_Y = 244

    try:

        pyautogui.click(
            SONG_X,
            SONG_Y
        )

        time.sleep(1)

        return (
            f"Playing {song}."
        )

    except Exception as e:

        return (
            "ERROR: Spotify playback failed: "
            f"{e}"
        )


# =========================================================
# MEMORY
# =========================================================

def save_memory(
    content: str,
    category: str = "general"
) -> str:

    if not content:

        return "ERROR: Empty memory."

    try:

        return str(
            remember(
                content,
                category
            )
        )

    except Exception as e:

        return (
            "ERROR: Could not save memory: "
            f"{e}"
        )


def search_memory(
    query: str
) -> str:

    if not query:

        return (
            "ERROR: Empty memory query."
        )

    try:

        return str(
            recall(
                query
            )
        )

    except Exception as e:

        return (
            "ERROR: Could not search memory: "
            f"{e}"
        )


# =========================================================
# CODE TOOLS
# =========================================================

def create_code_file(
    path: str,
    content: str
) -> str:

    return str(
        create_file(
            path=path,
            content=content
        )
    )


def read_code_file(
    path: str
) -> str:

    return str(
        read_file(
            path=path
        )
    )


def write_code_file(
    path: str,
    content: str
) -> str:

    return str(
        write_file(
            path=path,
            content=content
        )
    )


def open_code_in_vscode(
    path: str = "."
) -> str:

    return str(
        open_in_vscode(
            path=path
        )
    )


def run_python_file(
    path: str
) -> str:

    return str(
        run_python(
            path=path
        )
    )


def list_project_files(
    path: str = "."
) -> str:

    return str(
        list_files(
            path=path
        )
    )