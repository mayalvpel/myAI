import csv
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


# =========================================================
# APP ALIASES
# =========================================================

APP_ALIASES = {
    "whatsapp": [
        "WhatsApp",
        "WhatsApp.exe",
    ],

    "telegram": [
        "Telegram",
        "Telegram.exe",
        "Telegram Desktop",
    ],

    "telegram desktop": [
        "Telegram",
        "Telegram.exe",
        "Telegram Desktop",
    ],

    "chrome": [
        "Google Chrome",
        "chrome",
        "chrome.exe",
    ],

    "google chrome": [
        "Google Chrome",
        "chrome",
        "chrome.exe",
    ],

    "edge": [
        "Microsoft Edge",
        "msedge",
        "msedge.exe",
    ],

    "firefox": [
        "Mozilla Firefox",
        "firefox",
        "firefox.exe",
    ],

    "discord": [
        "Discord",
        "Discord.exe",
    ],
}


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_app_name(name):

    name = str(
        name or ""
    ).strip().lower()

    name = re.sub(
        r"\.exe$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    name = name.strip(
        " .,!?"
    )

    return name


def clean_display_name(name):

    name = str(
        name or ""
    ).strip()

    name = re.sub(
        r"\.exe$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    return name


# =========================================================
# PROCESS CHECK
# =========================================================

def get_running_processes():

    try:

        result = subprocess.run(
            [
                "tasklist",
                "/FO",
                "CSV",
                "/NH",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )

        if result.returncode != 0:
            return set()

        processes = set()

        for line in result.stdout.splitlines():

            try:

                row = next(
                    csv.reader(
                        [line]
                    )
                )

            except Exception:
                continue

            if not row:
                continue

            processes.add(
                row[0].lower()
            )

        return processes

    except Exception:

        return set()


# =========================================================
# START MENU
# =========================================================

def get_start_menu_apps():

    apps = {}

    try:

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                (
                    "Get-StartApps | "
                    "Select-Object Name,AppID | "
                    "ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        if result.returncode != 0:
            return apps

        import json

        raw = result.stdout.strip()

        if not raw:
            return apps

        data = json.loads(raw)

        if isinstance(data, dict):
            data = [data]

        for item in data:

            name = str(
                item.get("Name", "")
            ).strip()

            app_id = str(
                item.get("AppID", "")
            ).strip()

            if name:

                apps[
                    normalize_app_name(name)
                ] = {
                    "name": name,
                    "app_id": app_id,
                }

    except Exception:
        pass

    return apps


# =========================================================
# COMMON PATHS
# =========================================================

def search_common_paths(
    app_name,
):

    normalized = normalize_app_name(
        app_name
    )

    aliases = APP_ALIASES.get(
        normalized,
        [app_name],
    )

    roots = [
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("APPDATA", ""),
        os.environ.get("PROGRAMFILES", ""),
        os.environ.get("PROGRAMFILES(X86)", ""),
    ]

    candidates = []

    for alias in aliases:

        base = clean_display_name(
            alias
        )

        candidates.extend(
            [
                base,
                base.replace(
                    " ",
                    ""
                ),
            ]
        )

    # -----------------------------------------------------
    # Direct PATH lookup
    # -----------------------------------------------------

    for candidate in candidates:

        executable = shutil.which(
            candidate
        )

        if executable:

            return Path(
                executable
            )

    # -----------------------------------------------------
    # Search shallow installation paths
    # -----------------------------------------------------

    for root in roots:

        if not root:
            continue

        root_path = Path(root)

        if not root_path.exists():
            continue

        try:

            for candidate in candidates:

                possible = root_path / candidate

                if possible.exists():

                    if possible.is_file():

                        return possible

                    for exe in possible.glob(
                        "*.exe"
                    ):

                        return exe

        except Exception:
            continue

    return None


# =========================================================
# FIND APPLICATION
# =========================================================

def find_application(
    app_name,
):

    normalized = normalize_app_name(
        app_name
    )

    aliases = APP_ALIASES.get(
        normalized,
        [app_name],
    )

    # -----------------------------------------------------
    # 1. Start Menu
    # -----------------------------------------------------

    start_apps = get_start_menu_apps()

    for alias in aliases:

        alias_normalized = normalize_app_name(
            alias
        )

        for name, info in start_apps.items():

            if (
                alias_normalized == name
                or alias_normalized in name
                or name in alias_normalized
            ):

                return {
                    "installed": True,
                    "method": "start_menu",
                    "name": info["name"],
                    "app_id": info["app_id"],
                }

    # -----------------------------------------------------
    # 2. Common executable paths
    # -----------------------------------------------------

    executable = search_common_paths(
        app_name
    )

    if executable:

        return {
            "installed": True,
            "method": "executable",
            "path": str(executable),
            "name": app_name,
        }

    # -----------------------------------------------------
    # 3. Process
    # -----------------------------------------------------

    processes = get_running_processes()

    for alias in aliases:

        alias_exe = clean_display_name(
            alias
        ).lower()

        if not alias_exe.endswith(
            ".exe"
        ):

            alias_exe += ".exe"

        if alias_exe in processes:

            return {
                "installed": True,
                "method": "process",
                "name": app_name,
            }

    return {
        "installed": False,
        "name": app_name,
    }


# =========================================================
# OPEN
# =========================================================

def open_application(
    app_name,
):

    app_name = clean_display_name(
        app_name
    )

    found = find_application(
        app_name
    )

    if not found.get("installed"):

        return {
            "success": False,
            "not_installed": True,
            "error": (
                f"{app_name} was not found."
            ),
        }

    # -----------------------------------------------------
    # Start Menu app
    # -----------------------------------------------------

    if found.get("method") == "start_menu":

        app_id = found.get(
            "app_id"
        )

        if app_id:

            try:

                subprocess.Popen(
                    [
                        "explorer.exe",
                        f"shell:AppsFolder\\{app_id}",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                time.sleep(2)

                return {
                    "success": True,
                    "method": "start_menu",
                    "app": app_name,
                }

            except Exception as e:

                return {
                    "success": False,
                    "error": str(e),
                }

    # -----------------------------------------------------
    # Executable
    # -----------------------------------------------------

    path = found.get(
        "path"
    )

    if path:

        try:

            subprocess.Popen(
                [path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(2)

            return {
                "success": True,
                "method": "executable",
                "app": app_name,
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e),
            }

    # -----------------------------------------------------
    # Last resort: Windows start command
    # -----------------------------------------------------

    try:

        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                app_name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        time.sleep(2)

        return {
            "success": True,
            "method": "start",
            "app": app_name,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# CLOSE
# =========================================================

def close_application(
    app_name,
):

    normalized = normalize_app_name(
        app_name
    )

    aliases = APP_ALIASES.get(
        normalized,
        [app_name],
    )

    processes = get_running_processes()

    found_process = None

    for alias in aliases:

        exe = clean_display_name(
            alias
        ).lower()

        if not exe.endswith(
            ".exe"
        ):

            exe += ".exe"

        if exe in processes:

            found_process = exe
            break

    if not found_process:

        # Try common executable name.
        found_process = (
            clean_display_name(
                app_name
            )
            + ".exe"
        )

    try:

        result = subprocess.run(
            [
                "taskkill",
                "/IM",
                found_process,
                "/F",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )

        if result.returncode == 0:

            return {
                "success": True,
                "app": app_name,
            }

        return {
            "success": False,
            "error": (
                f"{app_name} does not appear "
                "to be running."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# INSTALL
# =========================================================

def install_application(
    app_name,
):

    app_name = clean_display_name(
        app_name
    )

    # -----------------------------------------------------
    # Check again immediately before installing
    # -----------------------------------------------------

    existing = find_application(
        app_name
    )

    if existing.get("installed"):

        return {
            "success": True,
            "already_installed": True,
            "app": app_name,
        }

    # -----------------------------------------------------
    # Winget
    # -----------------------------------------------------

    winget = shutil.which(
        "winget"
    )

    if not winget:

        return {
            "success": False,
            "error": (
                "winget is not available "
                "on this computer."
            ),
        }

    print(
        f"📦 Installing {app_name}..."
    )

    try:

        result = subprocess.run(
            [
                winget,
                "install",
                "--exact",
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements",
                "--name",
                app_name,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }

    # -----------------------------------------------------
    # Winget can sometimes return success while the
    # Start Menu registration happens a little later.
    # -----------------------------------------------------

    for _ in range(10):

        time.sleep(2)

        found = find_application(
            app_name
        )

        if found.get("installed"):

            return {
                "success": True,
                "already_installed": False,
                "registered": True,
                "app": app_name,
            }

    # -----------------------------------------------------
    # Winget result
    # -----------------------------------------------------

    if result.returncode == 0:

        return {
            "success": True,
            "already_installed": False,
            "registered": False,
            "app": app_name,
        }

    error = (
        result.stderr.strip()
        or result.stdout.strip()
        or "winget installation failed."
    )

    return {
        "success": False,
        "error": error[-2000:],
    }