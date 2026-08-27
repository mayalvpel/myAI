import csv
import json
import os
import platform
import re
import shutil
import subprocess
import time


# =========================================================
# ALIASES
# =========================================================

ALIASES = {

    "telegram":
        "Telegram",

    "telegram desktop":
        "Telegram",

    "telegram messenger":
        "Telegram",

    "whatsapp":
        "WhatsApp",

    "whats app":
        "WhatsApp",

    "chrome":
        "Google Chrome",

    "google chrome":
        "Google Chrome",

    "edge":
        "Microsoft Edge",

    "microsoft edge":
        "Microsoft Edge",

    "firefox":
        "Mozilla Firefox",

    "mozilla firefox":
        "Mozilla Firefox",

    "spotify":
        "Spotify",

    "discord":
        "Discord",

    "steam":
        "Steam",

    "notepad":
        "Notepad",

    "calculator":
        "Calculator",

    "vscode":
        "Visual Studio Code",

    "vs code":
        "Visual Studio Code",

    "visual studio code":
        "Visual Studio Code",
}


# =========================================================
# WINGET
# =========================================================

WINGET_IDS = {

    "Telegram":
        "Telegram.TelegramDesktop",

    "WhatsApp":
        "9NKSQGP7F2NH",

    "Google Chrome":
        "Google.Chrome",

    "Microsoft Edge":
        "Microsoft.Edge",

    "Mozilla Firefox":
        "Mozilla.Firefox",

    "Spotify":
        "Spotify.Spotify",

    "Discord":
        "Discord.Discord",

    "Steam":
        "Valve.Steam",

    "Notepad++":
        "Notepad++.Notepad++",

    "Visual Studio Code":
        "Microsoft.VisualStudioCode",
}


# =========================================================
# EXE PATHS
# =========================================================

EXE_PATHS = {

    "Telegram": [
        os.path.expandvars(
            r"%AppData%\Telegram Desktop\Telegram.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Telegram Desktop\Telegram.exe"
        ),
    ],

    "WhatsApp": [
        os.path.expandvars(
            r"%LocalAppData%\WhatsApp\WhatsApp.exe"
        ),
    ],

    "Google Chrome": [
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),
        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
        ),
    ],

    "Microsoft Edge": [
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        ),
    ],

    "Mozilla Firefox": [
        os.path.expandvars(
            r"%ProgramFiles%\Mozilla Firefox\firefox.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"
        ),
    ],

    "Spotify": [
        os.path.expandvars(
            r"%AppData%\Spotify\Spotify.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Spotify\Spotify.exe"
        ),
    ],

    "Discord": [
        os.path.expandvars(
            r"%LocalAppData%\Discord\Update.exe"
        ),
    ],

    "Steam": [
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Steam\steam.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Steam\steam.exe"
        ),
    ],

    "Visual Studio Code": [
        os.path.expandvars(
            r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"
        ),
        os.path.expandvars(
            r"%ProgramFiles%\Microsoft VS Code\Code.exe"
        ),
    ],
}


# =========================================================
# NORMALIZE
# =========================================================

def normalize_app_name(
    app_name
):

    value = str(
        app_name or ""
    ).strip()

    value = re.sub(
        r"[.!?,;:]+$",
        "",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return ALIASES.get(
        value.lower(),
        value
    )


# =========================================================
# START APPS
# =========================================================

def get_start_apps():

    if platform.system() != "Windows":
        return []

    command = r"""
Get-StartApps |
Select-Object Name, AppID |
ConvertTo-Json -Compress
"""

    try:

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )

        if result.returncode != 0:
            return []

        output = result.stdout.strip()

        if not output:
            return []

        data = json.loads(
            output
        )

        if isinstance(
            data,
            dict
        ):

            data = [
                data
            ]

        return data

    except Exception as e:

        print(
            f"⚠️ Start Apps error: {e}"
        )

        return []


# =========================================================
# FIND START APP
# =========================================================

def find_start_app(
    app_name
):

    target = normalize_app_name(
        app_name
    ).lower()

    apps = get_start_apps()

    # -----------------------------------------------------
    # Exact
    # -----------------------------------------------------

    for app in apps:

        name = str(
            app.get(
                "Name",
                ""
            )
        ).strip()

        app_id = str(
            app.get(
                "AppID",
                ""
            )
        ).strip()

        if not app_id:
            continue

        if name.lower() == target:

            return {
                "name": name,
                "app_id": app_id,
            }

    # -----------------------------------------------------
    # Special aliases
    # -----------------------------------------------------

    keywords = {

        "Telegram": [
            "telegram",
        ],

        "WhatsApp": [
            "whatsapp",
        ],

        "Google Chrome": [
            "google chrome",
            "chrome",
        ],

        "Microsoft Edge": [
            "microsoft edge",
        ],

        "Spotify": [
            "spotify",
        ],

        "Discord": [
            "discord",
        ],
    }

    for keyword in keywords.get(
        normalize_app_name(app_name),
        []
    ):

        for app in apps:

            name = str(
                app.get(
                    "Name",
                    ""
                )
            ).strip()

            app_id = str(
                app.get(
                    "AppID",
                    ""
                )
            ).strip()

            if (
                keyword in name.lower()
                and app_id
            ):

                return {
                    "name": name,
                    "app_id": app_id,
                }

    return None


# =========================================================
# FIND EXE
# =========================================================

def find_executable(
    app_name
):

    app_name = normalize_app_name(
        app_name
    )

    for path in EXE_PATHS.get(
        app_name,
        []
    ):

        if (
            path
            and os.path.isfile(path)
        ):

            return path

    # PATH
    names = [
        app_name,
        app_name.lower(),
        app_name.replace(
            " ",
            ""
        ),
    ]

    for name in names:

        found = shutil.which(
            name
        )

        if found:
            return found

    return None


# =========================================================
# APPX
# =========================================================

def find_appx(
    app_name
):

    if platform.system() != "Windows":
        return None

    name = normalize_app_name(
        app_name
    )

    # -----------------------------------------------------
    # Known package matching
    # -----------------------------------------------------

    patterns = {

        "Telegram": [
            "Telegram",
        ],

        "WhatsApp": [
            "WhatsApp",
        ],

        "Spotify": [
            "Spotify",
        ],

        "Discord": [
            "Discord",
        ],
    }

    search_patterns = patterns.get(
        name,
        [name]
    )

    for pattern in search_patterns:

        safe = pattern.replace(
            "'",
            "''"
        )

        command = f"""
Get-AppxPackage |
Where-Object {{
    $_.Name -like '*{safe}*' -or
    $_.PackageFullName -like '*{safe}*'
}} |
Select-Object -First 1 Name, PackageFullName |
ConvertTo-Json -Compress
"""

        try:

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )

            if result.returncode != 0:
                continue

            output = result.stdout.strip()

            if not output:
                continue

            return json.loads(
                output
            )

        except Exception:
            continue

    return None


# =========================================================
# FIND APP
# =========================================================

def find_app(
    app_name
):

    name = normalize_app_name(
        app_name
    )

    # -----------------------------------------------------
    # 1. EXE
    # -----------------------------------------------------

    executable = find_executable(
        name
    )

    if executable:

        return {
            "installed": True,
            "type": "exe",
            "name": name,
            "path": executable,
        }

    # -----------------------------------------------------
    # 2. Start Menu
    # -----------------------------------------------------

    start_app = find_start_app(
        name
    )

    if start_app:

        return {
            "installed": True,
            "type": "start_app",
            "name": start_app["name"],
            "app_id": start_app["app_id"],
        }

    # -----------------------------------------------------
    # 3. AppX
    # -----------------------------------------------------

    appx = find_appx(
        name
    )

    if appx:

        return {
            "installed": True,
            "type": "appx",
            "name": name,
            "package": appx,
        }

    return None


# =========================================================
# INSTALLED
# =========================================================

def is_app_installed(
    app_name
):

    result = find_app(
        app_name
    )

    return result is not None


# =========================================================
# OPEN
# =========================================================

def open_app(
    app_name
):

    name = normalize_app_name(
        app_name
    )

    print(
        f"🔍 Searching for {name}..."
    )

    app = find_app(
        name
    )

    if not app:

        print(
            f"❌ {name} was not found."
        )

        return {
            "success": False,
            "not_installed": True,
            "app_name": name,
        }

    print(
        f"✅ Found {name} "
        f"using {app['type']}"
    )

    # -----------------------------------------------------
    # EXE
    # -----------------------------------------------------

    if app["type"] == "exe":

        try:

            subprocess.Popen(
                [app["path"]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return {
                "success": True,
                "app_name": name,
                "method": "exe",
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
            }

    # -----------------------------------------------------
    # Start Menu / AppX
    # -----------------------------------------------------

    if app["type"] in {
        "start_app",
        "appx",
    }:

        start_app = find_start_app(
            name
        )

        if not start_app:

            # Try using package information to find
            # a Start Menu entry.
            start_app = find_start_app(
                app.get(
                    "name",
                    name
                )
            )

        if start_app:

            try:

                subprocess.Popen(
                    [
                        "explorer.exe",
                        (
                            "shell:AppsFolder\\"
                            f"{start_app['app_id']}"
                        ),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                return {
                    "success": True,
                    "app_name": name,
                    "method": "start_menu",
                }

            except Exception as e:

                return {
                    "success": False,
                    "error": str(e),
                }

    return {
        "success": False,
        "error": (
            f"Found {name}, but don't know "
            "how to launch it."
        ),
    }


# =========================================================
# INSTALL
# =========================================================

def install_app(
    app_name
):

    name = normalize_app_name(
        app_name
    )

    # -----------------------------------------------------
    # Never silently install here.
    #
    # core.py is responsible for confirmation.
    # -----------------------------------------------------

    winget = shutil.which(
        "winget"
    )

    if not winget:

        return {
            "success": False,
            "error": "winget was not found."
        }

    package_id = WINGET_IDS.get(
        name
    )

    if not package_id:

        return {
            "success": False,
            "error": (
                f"I don't have a verified winget "
                f"package ID for {name}."
            )
        }

    print(
        f"📦 Installing {name}..."
    )

    try:

        result = subprocess.run(
            [
                winget,
                "install",
                "--id",
                package_id,
                "-e",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0:

            return {
                "success": False,
                "error": (
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "Installation failed."
                ),
            }

        # -------------------------------------------------
        # Windows may need time to update Start Menu.
        # -------------------------------------------------

        print(
            "🔄 Verifying installation..."
        )

        for _ in range(20):

            time.sleep(1)

            if is_app_installed(
                name
            ):

                return {
                    "success": True,
                    "app_name": name,
                    "registered": True,
                }

        return {
            "success": True,
            "app_name": name,
            "registered": False,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# CLOSE
# =========================================================

def close_app(
    app_name
):

    name = normalize_app_name(
        app_name
    )

    process_map = {

        "Telegram": [
            "Telegram.exe",
        ],

        "WhatsApp": [
            "WhatsApp.exe",
        ],

        "Spotify": [
            "Spotify.exe",
        ],

        "Discord": [
            "Discord.exe",
        ],

        "Google Chrome": [
            "chrome.exe",
        ],

        "Microsoft Edge": [
            "msedge.exe",
        ],

        "Mozilla Firefox": [
            "firefox.exe",
        ],

        "Steam": [
            "steam.exe",
        ],
    }

    processes = process_map.get(
        name
    )

    if not processes:

        return {
            "success": False,
            "error": (
                f"I don't know the process "
                f"name for {name}."
            ),
        }

    closed = False

    for process in processes:

        try:

            result = subprocess.run(
                [
                    "taskkill",
                    "/IM",
                    process,
                    "/F",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:

                closed = True

        except Exception:
            pass

    return {
        "success": closed,
        "app_name": name,
    }