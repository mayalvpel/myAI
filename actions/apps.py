import os
import json
import shutil
import subprocess
import re
import time


# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

LEARNED_APPS_FILE = os.path.join(
    BASE_DIR,
    "learned_apps.json"
)


# =========================================================
# KNOWN APPS
# =========================================================

APPS = {

    "calculator": {
        "commands": [
            "calc.exe"
        ],
        "winget": None,
    },

    "notepad": {
        "commands": [
            "notepad.exe"
        ],
        "winget": None,
    },

    "chrome": {
        "commands": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "winget": "Google.Chrome",
    },

    "spotify": {
        "commands": [
            "spotify:",
            os.path.expandvars(
                r"%APPDATA%\Spotify\Spotify.exe"
            ),
            r"C:\Program Files\Spotify\Spotify.exe",
        ],
        "winget": "Spotify.Spotify",
    },

    "vlc": {
        "commands": [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ],
        "winget": "VideoLAN.VLC",
    },

}


# =========================================================
# LOAD LEARNED APPS
# =========================================================

def load_learned_apps():

    if not os.path.exists(
        LEARNED_APPS_FILE
    ):
        return {}

    try:

        with open(
            LEARNED_APPS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception as e:

        print(
            f"⚠️ Could not load learned apps: {e}"
        )

    return {}


LEARNED_APPS = load_learned_apps()


# =========================================================
# SAVE LEARNED APP
# =========================================================

def save_learned_app(
    name,
    winget=None,
    app_id=None,
    display_name=None
):

    name = name.lower().strip()

    existing = LEARNED_APPS.get(
        name,
        {}
    )

    LEARNED_APPS[name] = {

        "winget": (
            winget
            if winget is not None
            else existing.get("winget")
        ),

        "app_id": (
            app_id
            if app_id is not None
            else existing.get("app_id")
        ),

        "display_name": (
            display_name
            or existing.get("display_name")
            or name
        )
    }

    try:

        with open(
            LEARNED_APPS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                LEARNED_APPS,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"💾 Learned application: {name}"
        )

    except Exception as e:

        print(
            f"⚠️ Could not save learned app: {e}"
        )


# =========================================================
# WINDOWS START APPS
# =========================================================

def get_start_apps():

    try:

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Get-StartApps | ConvertTo-Json -Compress"
            ],
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            return []

        output = result.stdout.strip()

        if not output:
            return []

        data = json.loads(output)

        if isinstance(data, dict):
            data = [data]

        apps = []

        for item in data:

            name = str(
                item.get(
                    "Name",
                    ""
                )
            ).strip()

            app_id = str(
                item.get(
                    "AppID",
                    ""
                )
            ).strip()

            if name and app_id:

                apps.append({
                    "name": name,
                    "app_id": app_id
                })

        return apps

    except Exception as e:

        print(
            f"⚠️ Could not read Windows Start Apps: {e}"
        )

        return []


# =========================================================
# FIND START APP
# =========================================================

def find_start_app(
    app_name
):

    target = app_name.lower().strip()

    apps = get_start_apps()

    # Exact match
    for app in apps:

        if (
            app["name"].lower()
            == target
        ):
            return app

    # Starts with
    for app in apps:

        if app["name"].lower().startswith(
            target
        ):
            return app

    # Contains
    for app in apps:

        if target in app["name"].lower():
            return app

    return None


# =========================================================
# WINGET SEARCH
# =========================================================

def search_winget(
    app_name
):

    app_name = app_name.strip()

    print(
        f"🔎 Searching Windows packages for: "
        f"{app_name}"
    )

    try:

        result = subprocess.run(
            [
                "winget",
                "search",
                "--name",
                app_name,
                "--accept-source-agreements"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout

        print(output)

        lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        candidates = []

        for line in lines:

            if "Name" in line and "Id" in line:
                continue

            if line.startswith("-"):
                continue

            parts = re.split(
                r"\s{2,}",
                line
            )

            if len(parts) < 2:
                continue

            name = parts[0].strip()
            package_id = parts[1].strip()

            if not name or not package_id:
                continue

            candidates.append({
                "name": name,
                "winget": package_id
            })

        # =================================================
        # TELEGRAM
        # Prefer Telegram Desktop over Unigram
        # =================================================

        if app_name.lower() in {
            "telegram",
            "telegram desktop"
        }:

            for candidate in candidates:

                if (
                    candidate["name"].lower()
                    == "telegram desktop"
                    and
                    candidate["winget"].lower()
                    == "telegram.telegramdesktop"
                ):

                    print(
                        "🎯 Preferred Telegram match: "
                        f"{candidate['name']} "
                        f"({candidate['winget']})"
                    )

                    return candidate

        # =================================================
        # EXACT MATCH
        # =================================================

        for candidate in candidates:

            if (
                candidate["name"].lower()
                == app_name.lower()
            ):

                print(
                    f"🎯 Exact match found: "
                    f"{candidate['name']} "
                    f"({candidate['winget']})"
                )

                return candidate

        # =================================================
        # STRONG MATCH
        # =================================================

        for candidate in candidates:

            if (
                app_name.lower()
                in candidate["name"].lower()
            ):

                print(
                    f"🎯 Match found: "
                    f"{candidate['name']} "
                    f"({candidate['winget']})"
                )

                return candidate

    except FileNotFoundError:

        print(
            "❌ winget is not available."
        )

    except Exception as e:

        print(
            f"❌ Winget search error: {e}"
        )

    return None


# =========================================================
# FIND EXE / COMMAND
# =========================================================

def find_app_command(
    app_name
):

    name = app_name.lower().strip()

    # =====================================================
    # KNOWN APP
    # =====================================================

    if name in APPS:

        for command in APPS[name]["commands"]:

            if command.lower().endswith(
                ".exe"
            ):

                if os.path.exists(command):

                    return {
                        "type": "exe",
                        "value": command
                    }

            else:

                if shutil.which(command):

                    return {
                        "type": "command",
                        "value": command
                    }

    # =====================================================
    # LEARNED APP
    # =====================================================

    if name in LEARNED_APPS:

        learned = LEARNED_APPS[name]

        app_id = learned.get(
            "app_id"
        )

        if app_id:

            return {
                "type": "start_app",
                "value": app_id
            }

    return None


# =========================================================
# OPEN START APP
# =========================================================

def open_start_app(
    app_id
):

    try:

        subprocess.Popen(
            [
                "explorer.exe",
                f"shell:AppsFolder\\{app_id}"
            ]
        )

        return True

    except Exception as e:

        print(
            f"❌ Could not open Start App: {e}"
        )

        return False


# =========================================================
# FIND APPLICATION
# =========================================================

def find_app(
    app_name
):

    return find_app_command(
        app_name
    )


# =========================================================
# CHECK INSTALLED
# =========================================================

def is_installed(
    app_name
):

    command = find_app_command(
        app_name
    )

    if command:
        return True

    start_app = find_start_app(
        app_name
    )

    if start_app:

        save_learned_app(
            app_name,
            app_id=start_app["app_id"],
            display_name=start_app["name"]
        )

        return True

    return False


# =========================================================
# LEARN UNKNOWN APPLICATION
# =========================================================

def learn_unknown_app(
    app_name
):

    # Check Start Menu first
    start_app = find_start_app(
        app_name
    )

    if start_app:

        print(
            "🎯 Found installed Windows app: "
            f"{start_app['name']}"
        )

        save_learned_app(
            app_name,
            app_id=start_app["app_id"],
            display_name=start_app["name"]
        )

        return {
            "name": start_app["name"],
            "app_id": start_app["app_id"],
            "winget": None
        }

    # Search Winget
    package = search_winget(
        app_name
    )

    if package:

        save_learned_app(
            app_name,
            winget=package["winget"],
            display_name=package["name"]
        )

        return {
            "name": package["name"],
            "winget": package["winget"],
            "app_id": None
        }

    return None


# =========================================================
# OPEN APPLICATION
# =========================================================

def open_app(
    app_name
):

    name = app_name.lower().strip()

    # =====================================================
    # 1. KNOWN / LEARNED APP
    # =====================================================

    command = find_app_command(
        name
    )

    if command:

        try:

            if command["type"] == "exe":

                subprocess.Popen(
                    [
                        command["value"]
                    ]
                )

            elif command["type"] == "command":

                os.startfile(
                    command["value"]
                )

            elif command["type"] == "start_app":

                if not open_start_app(
                    command["value"]
                ):

                    raise Exception(
                        "Could not open Start App"
                    )

            return (
                True,
                f"Opening {name}.",
                None
            )

        except Exception as e:

            print(
                f"❌ Could not open {name}: {e}"
            )

    # =====================================================
    # 2. SEARCH WINDOWS START APPS
    # =====================================================

    start_app = find_start_app(
        name
    )

    if start_app:

        save_learned_app(
            name,
            app_id=start_app["app_id"],
            display_name=start_app["name"]
        )

        if open_start_app(
            start_app["app_id"]
        ):

            return (
                True,
                f"Opening {start_app['name']}.",
                None
            )

    # =====================================================
    # 3. SEARCH WINGET
    # =====================================================

    print(
        f"❓ I don't know {name}. Searching..."
    )

    package = search_winget(
        name
    )

    if package:

        save_learned_app(
            name,
            winget=package["winget"],
            display_name=package["name"]
        )

        # IMPORTANT:
        # DO NOT INSTALL HERE.
        #
        # Return a pending installation request.
        # The agent must stop and ask the user.

        return (
            False,

            (
                f"{package['name']} isn't installed. "
                f"I found it in Windows packages. "
                f"Would you like me to install it?"
            ),

            {
                "target": name,
                "winget": package["winget"],
                "display_name": package["name"]
            }
        )

    # =====================================================
    # NOTHING FOUND
    # =====================================================

    return (
        False,
        f"I couldn't find an application called {name}.",
        None
    )


# =========================================================
# INSTALL APPLICATION
# =========================================================

def install_app(
    app_name,
    winget_id=None
):

    name = app_name.lower().strip()

    # =====================================================
    # GET WINGET ID
    # =====================================================

    if not winget_id:

        if name in LEARNED_APPS:

            winget_id = LEARNED_APPS[
                name
            ].get("winget")

    if not winget_id:

        package = search_winget(
            name
        )

        if package:

            winget_id = package[
                "winget"
            ]

    if not winget_id:

        return (
            False,
            f"I don't know how to install {name}."
        )

    print(
        f"📦 Installing {name}..."
    )

    try:

        result = subprocess.run(
            [
                "winget",
                "install",
                "--id",
                winget_id,
                "--exact",
                "--accept-source-agreements",
                "--accept-package-agreements"
            ],
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:

            return (
                False,
                f"I couldn't install {name}. "
                f"winget exit code: "
                f"{result.returncode}"
            )

        # =================================================
        # REFRESH WINDOWS START APPS
        # =================================================

        print(
            "🔄 Refreshing Windows applications..."
        )

        start_app = None

        for _ in range(10):

            start_app = find_start_app(
                name
            )

            if start_app:
                break

            time.sleep(2)

        # =================================================
        # LEARN NEWLY INSTALLED APP
        # =================================================

        if start_app:

            save_learned_app(
                name,
                winget=winget_id,
                app_id=start_app["app_id"],
                display_name=start_app["name"]
            )

            return (
                True,
                f"{start_app['name']} has been installed.",
                start_app
            )

        # =================================================
        # INSTALLATION SUCCEEDED BUT START MENU NOT READY
        # =================================================

        save_learned_app(
            name,
            winget=winget_id
        )

        return (
            True,
            f"{name.capitalize()} has been installed.",
            None
        )

    except FileNotFoundError:

        return (
            False,
            "Windows Package Manager (winget) isn't available.",
            None
        )

    except subprocess.TimeoutExpired:

        return (
            False,
            f"Installation of {name} timed out.",
            None
        )

    except Exception as e:

        print(
            f"❌ Installation error: {e}"
        )

        return (
            False,
            f"I couldn't install {name}: {e}",
            None
        )