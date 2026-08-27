import subprocess
import os
import webbrowser
import urllib.parse


# =========================================================
# אפליקציות שהסוכן מורשה לפתוח
# =========================================================

APPS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",

    "chrome":
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",

    "vscode":
        r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
}


# =========================================================
# שמות חלופיים
# =========================================================

APP_ALIASES = {

    "calc": "calculator",
    "calculator": "calculator",

    "notepad": "notepad",

    "paint": "paint",
    "mspaint": "paint",

    "file explorer": "explorer",
    "windows explorer": "explorer",
    "explorer": "explorer",

    "chrome": "chrome",
    "google chrome": "chrome",

    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
}


# =========================================================
# פתיחת אפליקציה
# =========================================================

def open_app(app_name):

    app_name = app_name.lower().strip()

    app_name = APP_ALIASES.get(
        app_name,
        app_name
    )

    if app_name not in APPS:

        return (
            False,
            f"I don't know how to open {app_name}."
        )

    command = os.path.expandvars(
        APPS[app_name]
    )

    try:

        subprocess.Popen(command)

        return (
            True,
            f"Opening {app_name}."
        )

    except Exception as e:

        print(f"❌ Error: {e}")

        return (
            False,
            f"I couldn't open {app_name}."
        )


# =========================================================
# סגירת אפליקציה
# =========================================================

def close_app(app_name):

    app_name = app_name.lower().strip()

    app_name = APP_ALIASES.get(
        app_name,
        app_name
    )

    processes = {

        "calculator": "CalculatorApp.exe",
        "notepad": "notepad.exe",
        "paint": "mspaint.exe",
        "chrome": "chrome.exe",
        "vscode": "Code.exe",
        "explorer": "explorer.exe",
    }

    if app_name not in processes:

        return (
            False,
            f"I don't know how to close {app_name}."
        )

    process = processes[app_name]

    try:

        subprocess.run(
            [
                "taskkill",
                "/IM",
                process,
                "/F"
            ],
            capture_output=True,
            text=True
        )

        return (
            True,
            f"Closed {app_name}."
        )

    except Exception as e:

        print(f"❌ Error: {e}")

        return (
            False,
            f"I couldn't close {app_name}."
        )


# =========================================================
# פתיחת אתר
# =========================================================

def open_website(url):

    if not url.startswith("http"):

        url = "https://" + url

    try:

        webbrowser.open(url)

        return (
            True,
            "Opening the website."
        )

    except Exception as e:

        print(f"❌ Error: {e}")

        return (
            False,
            "I couldn't open the website."
        )


# =========================================================
# חיפוש בגוגל
# =========================================================

def search_google(query):

    if not query:

        return (
            False,
            "I need something to search for."
        )

    encoded_query = urllib.parse.quote_plus(
        query
    )

    url = (
        "https://www.google.com/search?q="
        + encoded_query
    )

    try:

        webbrowser.open(url)

        return (
            True,
            f"Searching Google for {query}."
        )

    except Exception as e:

        print(f"❌ Error: {e}")

        return (
            False,
            "I couldn't perform the search."
        )


# =========================================================
# COMMAND PROCESSOR
# =========================================================

def handle_command(text):

    text = text.lower().strip()

    text = text.rstrip(".!?")

    # =====================================================
    # OPEN APP
    # =====================================================

    open_phrases = [
        "open ",
        "please open ",
        "launch ",
        "please launch ",
        "start ",
        "please start ",
    ]

    for phrase in open_phrases:

        if text.startswith(phrase):

            app_name = text[
                len(phrase):
            ].strip()

            if app_name.startswith("the "):

                app_name = app_name[4:]

            if app_name in APP_ALIASES:

                return open_app(app_name)

    # =====================================================
    # CLOSE APP
    # =====================================================

    close_phrases = [
        "close ",
        "please close ",
        "quit ",
        "exit ",
        "stop ",
    ]

    for phrase in close_phrases:

        if text.startswith(phrase):

            app_name = text[
                len(phrase):
            ].strip()

            if app_name.startswith("the "):

                app_name = app_name[4:]

            if app_name in APP_ALIASES:

                return close_app(app_name)

    # =====================================================
    # GOOGLE SEARCH
    # =====================================================

    search_phrases = [
        "search google for ",
        "search for ",
        "google ",
    ]

    for phrase in search_phrases:

        if text.startswith(phrase):

            query = text[
                len(phrase):
            ].strip()

            return search_google(query)

    # =====================================================
    # WEBSITE
    # =====================================================

    website_commands = {

        "open youtube":
            "https://youtube.com",

        "open google":
            "https://google.com",

        "open gmail":
            "https://gmail.com",

        "open facebook":
            "https://facebook.com",

    }

    if text in website_commands:

        return open_website(
            website_commands[text]
        )

    # =====================================================
    # NO COMMAND
    # =====================================================

    return None