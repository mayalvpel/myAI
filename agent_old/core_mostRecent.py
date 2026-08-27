import ast
import ctypes
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import ollama

from agent.tools import (
    open_application as raw_open_application,
    youtube_search,
    web_search,
    spotify_play,
    install_python_package_tool,
    save_memory,
    search_memory,
    create_code_file,
    read_code_file,
    write_code_file,
    open_code_in_vscode,
    run_python_file,
    list_project_files,
)


# =========================================================
# SETTINGS
# =========================================================

MODEL = "qwen3:1.7b"

MAX_AGENT_STEPS = 10

PYTHON_REPAIR_ATTEMPTS = 3
PYTHON_GENERATION_ATTEMPTS = 3
PYTHON_DEPENDENCY_ATTEMPTS = 10
PYTHON_EXECUTION_ATTEMPTS = 5

PROJECT_DIR = Path.cwd().resolve()

LAST_CODE_FILE = None


# =========================================================
# APPLICATION OPENING / INSTALLATION SAFETY
# =========================================================
#
# CRITICAL FIX:
#
# The original open_application function is renamed to:
#
#     raw_open_application
#
# and all calls go through our wrapper:
#
#     open_application
#
# The wrapper:
#
# 1. Detects whether installation is actually required.
# 2. Never silently approves installation.
# 3. Preserves INSTALL_CONFIRMATION_REQUIRED.
# 4. Verifies that Telegram actually started.
# 5. Prevents the controller from reporting that Telegram
#    opened merely because the underlying tool said so.
#
# =========================================================


PENDING_INSTALLATION = None


# =========================================================
# APPLICATION NORMALIZATION
# =========================================================

def normalize_application_name(application):
    application = str(
        application or ""
    ).strip()

    if not application:
        return ""

    return re.sub(
        r"\s+",
        " ",
        application,
    ).strip()


def is_telegram_application(application):
    lower = normalize_application_name(
        application
    ).lower()

    telegram_names = {
        "telegram",
        "telegram desktop",
        "telegramdesktop",
        "telegram.exe",
        "telegramdesktop.exe",
        "telegram messenger",
    }

    if lower in telegram_names:
        return True

    return (
        "telegram" in lower
        and
        "web" not in lower
    )


# =========================================================
# PROCESS CHECKING
# =========================================================

def get_running_process_names():
    """
    Return a set of currently running Windows process
    executable names.

    This intentionally uses tasklist rather than psutil.
    """

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

        names = set()

        for line in result.stdout.splitlines():

            line = line.strip()

            if not line:
                continue

            try:
                row = next(
                    __import__("csv").reader(
                        [line]
                    )
                )

            except Exception:
                continue

            if not row:
                continue

            name = str(
                row[0]
            ).strip().lower()

            if name:
                names.add(name)

        return names

    except Exception:
        return set()


def is_telegram_running():
    """
    Verify that Telegram is actually running.

    We check known Telegram process names rather than
    trusting the return value of open_application().
    """

    process_names = get_running_process_names()

    known_processes = {
        "telegram.exe",
        "telegramdesktop.exe",
    }

    return bool(
        process_names.intersection(
            known_processes
        )
    )


def wait_for_telegram_process(
    timeout_seconds=8.0
):
    """
    Wait briefly for Telegram to actually start.

    Returns True only when a real Telegram process
    appears in tasklist.
    """

    deadline = (
        time.monotonic()
        + float(timeout_seconds)
    )

    while time.monotonic() < deadline:

        if is_telegram_running():
            return True

        time.sleep(0.4)

    return is_telegram_running()


# =========================================================
# INSTALLED APPLICATION DETECTION
# =========================================================

def executable_exists_on_path(
    executable_name
):

    executable_name = str(
        executable_name or ""
    ).strip()

    if not executable_name:
        return False

    try:

        result = subprocess.run(
            [
                "where.exe",
                executable_name,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        return (
            result.returncode == 0
            and
            bool(
                result.stdout.strip()
            )
        )

    except Exception:
        return False


def search_windows_start_apps(
    application
):
    """
    Uses Windows Get-StartApps to determine whether an
    application is registered in the Windows Start menu.

    This is particularly useful for Telegram installations
    that are not simply available through PATH.
    """

    application = normalize_application_name(
        application
    )

    if not application:
        return False

    try:

        escaped = application.replace(
            "'",
            "''",
        )

        powershell_script = (
            "$ErrorActionPreference = 'SilentlyContinue'; "
            "$apps = Get-StartApps; "
            f"$matches = $apps | Where-Object "
            f"{{ $_.Name -like '*{escaped}*' }}; "
            "if ($matches) { exit 0 } else { exit 1 }"
        )

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )

        return result.returncode == 0

    except Exception:
        return False


def telegram_installation_paths():
    """
    Return common Telegram installation locations.

    These are detection paths only. Nothing is executed
    from these paths merely because they exist.
    """

    paths = []

    local_app_data = os.environ.get(
        "LOCALAPPDATA",
        "",
    )

    app_data = os.environ.get(
        "APPDATA",
        "",
    )

    program_files = os.environ.get(
        "PROGRAMFILES",
        "",
    )

    program_files_x86 = os.environ.get(
        "PROGRAMFILES(X86)",
        "",
    )

    if local_app_data:

        paths.extend(
            [
                Path(local_app_data)
                / "Telegram Desktop"
                / "Telegram.exe",

                Path(local_app_data)
                / "Programs"
                / "Telegram Desktop"
                / "Telegram.exe",
            ]
        )

    if app_data:

        paths.extend(
            [
                Path(app_data)
                / "Telegram Desktop"
                / "Telegram.exe",
            ]
        )

    if program_files:

        paths.extend(
            [
                Path(program_files)
                / "Telegram Desktop"
                / "Telegram.exe",
            ]
        )

    if program_files_x86:

        paths.extend(
            [
                Path(program_files_x86)
                / "Telegram Desktop"
                / "Telegram.exe",
            ]
        )

    return paths


def is_telegram_installed():
    """
    Determine whether Telegram appears to already be installed.

    We intentionally do NOT call open_application here.

    That is important because calling the original tool just
    to check availability may itself trigger installation.
    """

    if executable_exists_on_path(
        "Telegram.exe"
    ):
        return True

    if executable_exists_on_path(
        "TelegramDesktop.exe"
    ):
        return True

    for path in telegram_installation_paths():

        try:

            if path.is_file():
                return True

        except Exception:
            pass

    if search_windows_start_apps(
        "Telegram"
    ):
        return True

    return False


def application_is_installed(
    application
):
    """
    Generic installed-application detection.

    Telegram gets a dedicated detection path because it is
    one of the applications for which we need strict
    verification.

    For other applications we use Windows Start Apps plus
    PATH-based executable detection.
    """

    application = normalize_application_name(
        application
    )

    if not application:
        return False

    if is_telegram_application(
        application
    ):
        return is_telegram_installed()

    executable_candidates = []

    cleaned = re.sub(
        r"\.exe$",
        "",
        application,
        flags=re.IGNORECASE,
    )

    compact = re.sub(
        r"[^A-Za-z0-9_-]+",
        "",
        cleaned,
    )

    if compact:

        executable_candidates.extend(
            [
                compact + ".exe",
                cleaned + ".exe",
            ]
        )

    for executable in executable_candidates:

        if executable_exists_on_path(
            executable
        ):
            return True

    if search_windows_start_apps(
        application
    ):
        return True

    return False


# =========================================================
# APPLICATION INSTALLATION CONFIRMATION RESULT
# =========================================================

def installation_confirmation_message(
    application
):
    return (
        f"{application} is not installed. "
        f"Would you like me to install it?"
    )


def build_installation_confirmation(
    application,
    arguments=None,
):
    arguments = arguments or {}

    package_id = (
        arguments.get("package_id")
        or arguments.get("package")
        or arguments.get("id")
    )

    return (
        "INSTALL_CONFIRMATION_REQUIRED:"
        f" {installation_confirmation_message(application)}"
    )


# =========================================================
# SAFE APPLICATION OPEN WRAPPER
# =========================================================

def open_application(
    application=None,
    **kwargs
):
    """
    Safe wrapper around the original open_application tool.

    IMPORTANT:

    This function must be the ONLY application-opening
    function exposed to Ollama.

    The original function is available internally as
    raw_open_application.
    """

    application = normalize_application_name(
        application
    )

    if not application:
        return (
            "ERROR: No application was specified."
        )

    # -----------------------------------------------------
    # CHECK WHETHER THIS IS A CONFIRMED INSTALLATION
    # -----------------------------------------------------

    confirm_install = kwargs.get(
        "confirm_install",
        False,
    )

    install = kwargs.get(
        "install",
        False,
    )

    # -----------------------------------------------------
    # NEVER allow an arbitrary AI-generated
    # confirm_install=True to silently install.
    #
    # The only valid path for installation is through
    # PENDING_INSTALLATION -> handle_pending_installation.
    # -----------------------------------------------------

    if (
        confirm_install
        or install
    ):
        return (
            "ERROR: Application installation must "
            "be explicitly confirmed by the user first."
        )

    # -----------------------------------------------------
    # CHECK INSTALLATION BEFORE CALLING RAW TOOL
    # -----------------------------------------------------

    installed = application_is_installed(
        application
    )

    if not installed:

        return (
            "INSTALL_CONFIRMATION_REQUIRED:"
            f" {installation_confirmation_message(application)}"
        )

    # -----------------------------------------------------
    # REMOVE INSTALLATION-RELATED FLAGS
    # -----------------------------------------------------

    safe_kwargs = dict(
        kwargs
    )

    safe_kwargs.pop(
        "confirm_install",
        None,
    )

    safe_kwargs.pop(
        "install",
        None,
    )

    # -----------------------------------------------------
    # CALL ORIGINAL TOOL
    # -----------------------------------------------------

    try:

        result = raw_open_application(
            application=application,
            **safe_kwargs,
        )

    except TypeError:

        # Compatibility with an older version that may
        # accept only application=.
        try:

            result = raw_open_application(
                application=application,
            )

        except Exception as e:

            return (
                "ERROR: Could not open "
                f"{application}: {e}"
            )

    except Exception as e:

        return (
            "ERROR: Could not open "
            f"{application}: {e}"
        )

    result_text = str(
        result or ""
    ).strip()

    # -----------------------------------------------------
    # IF UNDERLYING TOOL ITSELF REQUESTS INSTALLATION,
    # PROPAGATE THAT REQUEST.
    # -----------------------------------------------------

    if result_text.startswith(
        "INSTALL_CONFIRMATION_REQUIRED:"
    ):

        return result_text

    # -----------------------------------------------------
    # TELEGRAM MUST BE VERIFIED ACTUALLY RUNNING
    # -----------------------------------------------------

    if is_telegram_application(
        application
    ):

        # Give Windows a moment to create the process.
        telegram_started = (
            wait_for_telegram_process(
                timeout_seconds=8.0
            )
        )

        if telegram_started:

            return (
                f"{application} opened successfully."
            )

        # The underlying tool claimed success, but
        # tasklist says Telegram isn't running.
        return (
            "ERROR: Telegram did not actually open. "
            "The application-opening tool returned a "
            "success-like result, but no Telegram process "
            "was detected in Windows."
        )

    # -----------------------------------------------------
    # GENERIC APPLICATION:
    #
    # We cannot reliably know every application's process
    # name, so preserve the underlying result.
    # -----------------------------------------------------

    if result_text.startswith(
        "ERROR:"
    ):
        return result_text

    return result_text or (
        f"{application} opened successfully."
    )


# =========================================================
# TOOL REGISTRY
# =========================================================

ALL_TOOLS = [
    open_application,
    youtube_search,
    web_search,
    spotify_play,
    save_memory,
    search_memory,
    create_code_file,
    read_code_file,
    write_code_file,
    open_code_in_vscode,
    run_python_file,
    list_project_files,
    install_python_package_tool,
]


AVAILABLE_FUNCTIONS = {
    "open_application": open_application,
    "youtube_search": youtube_search,
    "web_search": web_search,
    "spotify_play": spotify_play,
    "save_memory": save_memory,
    "search_memory": search_memory,
    "create_code_file": create_code_file,
    "read_code_file": read_code_file,
    "write_code_file": write_code_file,
    "open_code_in_vscode": open_code_in_vscode,
    "run_python_file": run_python_file,
    "list_project_files": list_project_files,
    "install_python_package_tool": install_python_package_tool,
}


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = r"""
You are JARVIS.

You are a local AI assistant running on Windows.

Your job is to COMPLETE the user's CURRENT request.

You have access to a Python execution environment.

IMPORTANT:

When the user asks you to perform a computer operation,
actually perform it.

Do not merely explain how to perform it.

Do not return fake results.

Do not invent values.

============================================================
APPLICATION INSTALLATION
============================================================

IMPORTANT:

Never silently install an application.

If an application is not installed:

1. Return an installation confirmation request.
2. Wait for the user's explicit yes/no response.
3. Do not continue to another tool.
4. Do not use Python as a fallback to bypass confirmation.
5. Do not claim the application opened unless it was
   actually verified.

For Telegram specifically:

The controller verifies that a real Telegram process
exists after attempting to open it.

Do not claim Telegram opened based only on the tool result.

============================================================
PYTHON
============================================================

When Python is required:

1. Generate a complete executable Python program.

2. Third-party packages are allowed.

3. The controller automatically installs missing
   third-party Python packages before execution.

4. Do not avoid useful packages because they are not
   currently installed.

5. Use Windows-compatible APIs and commands.

6. Do not invent Linux paths.

7. Do not use /home.

8. Do not use /media.

9. Print the useful final result.

10. Do not return Markdown.

11. Do not return code fences.

12. Do not return explanations when generating source.

13. Do not use placeholders.

14. Actually perform the requested operation.

============================================================
LOCAL COMPUTER
============================================================

Local computer information must use real local APIs,
Windows commands, or Python libraries.

Do not use web search for local computer information.

Examples:

CPU usage
RAM usage
disk space
uptime
local IP
public IP
processes
services

============================================================
WINDOWS SERVICES
============================================================

For Windows services prefer:

sc.exe query state= all

or:

Get-Service

Do NOT unnecessarily use psutil for Windows services.

============================================================
WINDOWS PROCESSES
============================================================

For processes prefer:

tasklist /FO CSV /NH

Do NOT unnecessarily use psutil for process listing.

============================================================
FINAL RESPONSE
============================================================

Return only the useful result.

Do not expose:

tool calls
internal reasoning
prompts
Python source
debugging
dependency installation details
"""


# =========================================================
# TEXT HELPERS
# =========================================================

def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip(),
    )


def remove_thinking(text):
    text = str(text or "").strip()

    if "<think>" in text:
        if "</think>" in text:
            text = text.split("</think>", 1)[1]
        else:
            text = text.split("<think>", 1)[0]

    return text.strip()


def clean_generated_code(code):
    code = remove_thinking(code)

    code = re.sub(
        r"^\s*```(?:python|py)?\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"\s*```\s*$",
        "",
        code,
    )

    code = code.strip()

    lines = code.splitlines()

    if lines:
        if re.fullmatch(
            r"[A-Za-z0-9_.-]+\.py",
            lines[0].strip(),
            re.IGNORECASE,
        ):
            lines = lines[1:]

            if (
                lines
                and re.fullmatch(
                    r"=+",
                    lines[0].strip(),
                )
            ):
                lines = lines[1:]

            code = "\n".join(lines).strip()

    return code.strip()


# =========================================================
# PATH SAFETY
# =========================================================

def normalize_project_path(path):
    path = str(path or "").strip()

    if not path:
        return None

    if re.match(r"^[A-Za-z]:[\\/]", path):
        return None

    if path.startswith("/"):
        return None

    if path.startswith("\\\\"):
        return None

    try:
        candidate = (PROJECT_DIR / path).resolve()

        if candidate == PROJECT_DIR:
            return None

        if PROJECT_DIR not in candidate.parents:
            return None

        return str(candidate.relative_to(PROJECT_DIR))

    except Exception:
        return None


def project_file_exists(path):
    safe = normalize_project_path(path)

    if not safe:
        return False

    return (PROJECT_DIR / safe).exists()


# =========================================================
# MEMORY
# =========================================================

def detect_memory_save(text):
    text = normalize_text(text)

    patterns = [
        r"^remember that (.+)$",
        r"^remember (.+)$",
        r"^don't forget that (.+)$",
        r"^dont forget that (.+)$",
        r"^keep in mind that (.+)$",
        r"^save this[:\s]+(.+)$",
        r"^store this[:\s]+(.+)$",
    ]

    for pattern in patterns:
        match = re.match(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        content = match.group(1).strip()

        if not content:
            return None

        category = "general"

        lower = content.lower()

        if "project" in lower:
            category = "project"

        elif (
            "prefer" in lower
            or "preference" in lower
        ):
            category = "preference"

        elif (
            "my name" in lower
            or "i am" in lower
            or "i'm" in lower
        ):
            category = "user"

        return {
            "type": "save",
            "content": content,
            "category": category,
        }

    return None


def detect_memory_search(text):
    text = normalize_text(text).lower()

    if "what is my project" in text:
        return {
            "type": "search",
            "query": "project name",
        }

    if "what's my project" in text:
        return {
            "type": "search",
            "query": "project name",
        }

    if "who is your creator" in text:
        return {
            "type": "search",
            "query": "creator",
        }

    if "who created you" in text:
        return {
            "type": "search",
            "query": "creator",
        }

    if "who is your programmer" in text:
        return {
            "type": "search",
            "query": "programmer",
        }

    if "who programmed you" in text:
        return {
            "type": "search",
            "query": "programmer",
        }

    if "what do you remember" in text:
        return {
            "type": "search",
            "query": text,
        }

    return None


def handle_memory(text):
    save_intent = detect_memory_save(text)

    if save_intent:
        result = save_memory(
            content=save_intent["content"],
            category=save_intent["category"],
        )

        if str(result).startswith("ERROR:"):
            return "I was unable to save that information."

        return "I've saved that information."

    search_intent = detect_memory_search(text)

    if search_intent:
        result = search_memory(
            query=search_intent["query"],
        )

        result = str(result)

        if (
            not result
            or "No relevant memory found" in result
            or "No memory found" in result
        ):
            return (
                "I don't have that information stored "
                "in my memory."
            )

        lines = []

        for line in result.splitlines():
            line = re.sub(
                r"^\[[^\]]+\]\s*",
                "",
                line.strip(),
            )

            if line:
                lines.append(line)

        if not lines:
            return (
                "I don't have that information stored "
                "in my memory."
            )

        return lines[0]

    return None


# =========================================================
# REQUEST CLASSIFICATION
# =========================================================

def is_uptime_request(text):
    lower = normalize_text(text).lower()

    patterns = [
        r"\buptime\b",
        r"\bhow long has .*computer.*been running\b",
        r"\bhow long has .*pc.*been running\b",
        r"\bhow long has .*computer.*been on\b",
        r"\bhow long has .*pc.*been on\b",
        r"\bhow long.*system.*running\b",
        r"\bhow long.*windows.*running\b",
        r"\bwhen did.*computer.*start\b",
        r"\bwhen did.*pc.*start\b",
        r"\bwhen did.*windows.*start\b",
        r"\bwhen was.*computer.*started\b",
        r"\bsystem uptime\b",
        r"\bcomputer uptime\b",
    ]

    return any(
        re.search(pattern, lower)
        for pattern in patterns
    )


def is_external_ip_request(text):
    lower = normalize_text(text).lower()

    return any(
        phrase in lower
        for phrase in [
            "external ip",
            "public ip",
            "external address",
            "public address",
            "internet ip",
        ]
    )


def is_local_ip_request(text):
    lower = normalize_text(text).lower()

    if is_external_ip_request(text):
        return False

    return any(
        phrase in lower
        for phrase in [
            "my ip",
            "my ip address",
            "local ip",
            "local address",
            "local ip address",
        ]
    )


def is_disk_space_request(text):
    lower = normalize_text(text).lower()

    return (
        any(
            phrase in lower
            for phrase in [
                "free space",
                "disk space",
                "storage space",
                "space is left",
                "space left",
                "how much space",
            ]
        )
        and
        any(
            word in lower
            for word in [
                "drive",
                "disk",
                "storage",
                "space",
            ]
        )
    )


def is_cpu_request(text):
    lower = normalize_text(text).lower()

    patterns = [
        "cpu usage",
        "cpu utilization",
        "processor usage",
        "processor utilization",
        "how much cpu",
        "how much processor",
        "cpu load",
        "processor load",
    ]

    return any(
        phrase in lower
        for phrase in patterns
    )


def is_memory_usage_request(text):
    lower = normalize_text(text).lower()

    patterns = [
        "ram usage",
        "memory usage",
        "memory utilization",
        "how much ram",
        "how much memory",
        "ram am i using",
        "memory am i using",
    ]

    return any(
        phrase in lower
        for phrase in patterns
    )


def is_services_request(text):
    lower = normalize_text(text).lower()

    phrases = [
        "services running",
        "running services",
        "windows services",
        "list services",
        "list the services",
        "services on my computer",
        "services on my pc",
        "what services are running",
        "which services are running",
        "all the services",
        "all services",
        "list all services",
        "list all the services",
        "services running on my computer",
        "services running on my pc",
    ]

    return any(
        phrase in lower
        for phrase in phrases
    )


def is_process_request(text):
    lower = normalize_text(text).lower()

    phrases = [
        "running processes",
        "processes running",
        "list processes",
        "list the processes",
        "process information",
        "what processes are running",
        "which processes are running",
        "processes on my computer",
        "processes on my pc",
        "all processes",
        "all the processes",
        "list all processes",
        "list all the processes",
    ]

    return any(
        phrase in lower
        for phrase in phrases
    )


def is_system_request(text):
    return (
        is_uptime_request(text)
        or is_external_ip_request(text)
        or is_local_ip_request(text)
        or is_disk_space_request(text)
        or is_cpu_request(text)
        or is_memory_usage_request(text)
        or is_services_request(text)
        or is_process_request(text)
    )


# =========================================================
# DETERMINISTIC WINDOWS PYTHON
# =========================================================

def deterministic_python_source(user_request):

    if is_services_request(user_request):
        return r'''import subprocess
import re

result = subprocess.run(
    [
        "sc.exe",
        "query",
        "state=",
        "all",
        "bufsize=",
        "65536",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)

if result.returncode != 0:
    raise RuntimeError(
        result.stderr.strip()
        or result.stdout.strip()
        or f"sc.exe failed with exit code {result.returncode}"
    )

current_name = None
current_display_name = None
current_state = None

services = []

for raw_line in result.stdout.splitlines():

    line = raw_line.strip()

    if line.startswith("SERVICE_NAME:"):

        current_name = line.split(
            "SERVICE_NAME:",
            1,
        )[1].strip()

        current_display_name = None
        current_state = None

    elif line.startswith("DISPLAY_NAME:"):

        current_display_name = line.split(
            "DISPLAY_NAME:",
            1,
        )[1].strip()

    elif line.startswith("STATE"):

        match = re.search(
            r"STATE\s*:\s*\d+\s+([A-Za-z_]+)",
            line,
            re.IGNORECASE,
        )

        if match:
            current_state = match.group(1).upper()

            if current_name:
                services.append(
                    (
                        current_name,
                        current_display_name or "",
                        current_state,
                    )
                )

                current_name = None
                current_display_name = None
                current_state = None


services.sort(
    key=lambda item: item[0].lower()
)

for name, display_name, state in services:
    print(
        f"{name} | "
        f"{display_name} | "
        f"{state}"
    )

print(
    f"\nTotal services: {len(services)}"
)
'''

    if is_process_request(user_request):
        return r'''import subprocess
import csv
import io

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
    timeout=60,
)

if result.returncode != 0:
    raise RuntimeError(
        result.stderr.strip()
        or "tasklist failed"
    )

reader = csv.reader(
    io.StringIO(result.stdout)
)

count = 0

for row in reader:

    if not row:
        continue

    if len(row) >= 2:
        image_name = row[0]
        pid = row[1]

        print(
            f"{image_name} | PID {pid}"
        )

        count += 1

print(
    f"\nTotal processes: {count}"
)
'''

    if is_uptime_request(user_request):
        return r'''import ctypes

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)

kernel32.GetTickCount64.restype = ctypes.c_ulonglong
kernel32.GetTickCount64.argtypes = []

milliseconds = kernel32.GetTickCount64()

total_seconds = milliseconds // 1000

days, remainder = divmod(
    total_seconds,
    86400,
)

hours, remainder = divmod(
    remainder,
    3600,
)

minutes, seconds = divmod(
    remainder,
    60,
)

parts = []

if days:
    parts.append(
        f"{days} day" + ("s" if days != 1 else "")
    )

if hours:
    parts.append(
        f"{hours} hour" + ("s" if hours != 1 else "")
    )

if minutes:
    parts.append(
        f"{minutes} minute" + ("s" if minutes != 1 else "")
    )

if seconds or not parts:
    parts.append(
        f"{seconds} second" + ("s" if seconds != 1 else "")
    )

print(", ".join(parts))
'''

    if is_external_ip_request(user_request):
        return r'''import urllib.request

request = urllib.request.Request(
    "https://api.ipify.org",
    headers={
        "User-Agent": "Jarvis/1.0",
    },
)

with urllib.request.urlopen(
    request,
    timeout=10,
) as response:

    ip = response.read().decode(
        "utf-8"
    ).strip()

print(ip)
'''

    if is_local_ip_request(user_request):
        return r'''import socket

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM,
)

try:
    sock.connect(
        ("8.8.8.8", 80)
    )

    ip = sock.getsockname()[0]

finally:
    sock.close()

print(ip)
'''

    if is_disk_space_request(user_request):
        return r'''import shutil

total, used, free = shutil.disk_usage(
    "C:\\"
)

gb = 1024 ** 3

print(
    f"{free / gb:.2f} GB free of "
    f"{total / gb:.2f} GB"
)
'''

    if is_cpu_request(user_request):
        return r'''import ctypes
import time

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)

GetSystemTimes = kernel32.GetSystemTimes

GetSystemTimes.argtypes = [
    ctypes.POINTER(ctypes.c_ulonglong),
    ctypes.POINTER(ctypes.c_ulonglong),
    ctypes.POINTER(ctypes.c_ulonglong),
]

GetSystemTimes.restype = ctypes.c_bool


def get_times():

    idle = ctypes.c_ulonglong()
    kernel = ctypes.c_ulonglong()
    user = ctypes.c_ulonglong()

    if not GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError()

    return (
        idle.value,
        kernel.value,
        user.value,
    )


idle1, kernel1, user1 = get_times()

time.sleep(0.25)

idle2, kernel2, user2 = get_times()

idle_delta = idle2 - idle1
kernel_delta = kernel2 - kernel1
user_delta = user2 - user1

total = kernel_delta + user_delta

if total <= 0:
    cpu = 0.0
else:
    busy = total - idle_delta
    cpu = (busy / total) * 100.0

cpu = max(
    0.0,
    min(100.0, cpu),
)

print(f"{cpu:.1f}%")
'''

    if is_memory_usage_request(user_request):
        return r'''import ctypes

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)


class MEMORYSTATUSEX(
    ctypes.Structure
):

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        (
            "ullTotalPhys",
            ctypes.c_ulonglong,
        ),
        (
            "ullAvailPhys",
            ctypes.c_ulonglong,
        ),
        (
            "ullTotalPageFile",
            ctypes.c_ulonglong,
        ),
        (
            "ullAvailPageFile",
            ctypes.c_ulonglong,
        ),
        (
            "ullTotalVirtual",
            ctypes.c_ulonglong,
        ),
        (
            "ullAvailVirtual",
            ctypes.c_ulonglong,
        ),
        (
            "ullAvailExtendedVirtual",
            ctypes.c_ulonglong,
        ),
    ]


status = MEMORYSTATUSEX()

status.dwLength = ctypes.sizeof(
    MEMORYSTATUSEX
)

if not kernel32.GlobalMemoryStatusEx(
    ctypes.byref(status)
):
    raise ctypes.WinError()

gb = 1024 ** 3

used = (
    status.ullTotalPhys
    - status.ullAvailPhys
)

print(
    f"{used / gb:.2f} GB used of "
    f"{status.ullTotalPhys / gb:.2f} GB "
    f"({status.dwMemoryLoad}% used)"
)
'''

    return None


# =========================================================
# PYTHON FILE NAME
# =========================================================

def choose_python_filename(user_request):

    if is_uptime_request(user_request):
        return "get_uptime.py"

    if is_external_ip_request(user_request):
        return "get_external_ip.py"

    if is_local_ip_request(user_request):
        return "get_local_ip.py"

    if is_disk_space_request(user_request):
        return "get_disk_space.py"

    if is_cpu_request(user_request):
        return "get_cpu_usage.py"

    if is_memory_usage_request(user_request):
        return "get_memory_usage.py"

    if is_services_request(user_request):
        return "get_services.py"

    if is_process_request(user_request):
        return "get_processes.py"

    return "python_task.py"


# =========================================================
# PYTHON VALIDATION
# =========================================================

def looks_like_placeholder_code(code):

    lower = code.lower()

    bad_patterns = [
        "x seconds",
        "x minutes",
        "x hours",
        "placeholder",
        "todo",
        "implement this",
        "implementation here",
        "return the result here",
        "your code here",
        "example only",
        "dummy value",
        "fake value",
    ]

    return any(
        pattern in lower
        for pattern in bad_patterns
    )


def validate_generated_python(code):

    code = clean_generated_code(code)

    if not code:
        return (
            False,
            "Generated Python source is empty.",
        )

    if looks_like_placeholder_code(code):
        return (
            False,
            "Generated Python contains placeholder code.",
        )

    try:
        compile(
            code,
            "<generated>",
            "exec",
        )

    except SyntaxError as e:
        return (
            False,
            f"Generated Python has a syntax error: {e}",
        )

    return True, None


# =========================================================
# IMPORT -> PIP
# =========================================================

IMPORT_TO_PIP = {

    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",

    "Crypto": "pycryptodome",

    "serial": "pyserial",

    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "win32process": "pywin32",
    "win32service": "pywin32",
    "win32serviceutil": "pywin32",

    "psutil": "psutil",
    "requests": "requests",
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "selenium": "selenium",
    "flask": "flask",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",

    "ollama": "ollama",
}


# =========================================================
# PIP
# =========================================================

def ensure_pip():

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "--version",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True

    except Exception:
        pass

    print(
        "📦 pip is unavailable. "
        "Bootstrapping pip..."
    )

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ensurepip",
                "--upgrade",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            return True

        print(result.stderr)

    except Exception as e:

        print(
            f"❌ Could not bootstrap pip: {e}"
        )

    return False


def install_python_package(package_name):

    package_name = str(
        package_name or ""
    ).strip()

    if not package_name:
        return False

    if not re.fullmatch(
        r"[A-Za-z0-9_.\-\[\]=<>!~]+",
        package_name,
    ):
        print(
            f"❌ Invalid package name: "
            f"{package_name}"
        )
        return False

    if not ensure_pip():
        return False

    print(
        f"📦 Installing Python package: "
        f"{package_name}"
    )

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                package_name,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:

            print(
                f"✅ Installed: {package_name}"
            )

            return True

        print(
            f"❌ pip failed installing "
            f"{package_name}"
        )

        if result.stderr:
            print(result.stderr)

    except subprocess.TimeoutExpired:

        print(
            f"❌ pip timed out installing "
            f"{package_name}"
        )

    except Exception as e:

        print(
            f"❌ Package installation error: "
            f"{e}"
        )

    return False


# =========================================================
# IMPORT DETECTION
# =========================================================

def extract_imports_from_source(source):

    imports = set()

    try:
        tree = ast.parse(source)

    except SyntaxError:
        return imports

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                root = alias.name.split(
                    "."
                )[0]

                if root:
                    imports.add(root)

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.level != 0:
                continue

            if node.module:

                root = node.module.split(
                    "."
                )[0]

                if root:
                    imports.add(root)

    return imports


# =========================================================
# STANDARD LIBRARY
# =========================================================

def is_standard_library_module(name):

    if not name:
        return True

    if name in sys.builtin_module_names:
        return True

    try:

        stdlib_path = Path(
            os.__file__
        ).resolve().parent

        candidate = (
            stdlib_path
            / name.replace(
                ".",
                os.sep,
            )
            + Path(".py")
        )

        if candidate.exists():
            return True

        package_dir = (
            stdlib_path
            / name
        )

        if package_dir.exists():
            return True

    except Exception:
        pass

    return name in {
        "abc",
        "argparse",
        "ast",
        "asyncio",
        "base64",
        "calendar",
        "collections",
        "concurrent",
        "configparser",
        "contextlib",
        "copy",
        "csv",
        "ctypes",
        "dataclasses",
        "datetime",
        "decimal",
        "difflib",
        "email",
        "enum",
        "errno",
        "functools",
        "gc",
        "getpass",
        "glob",
        "gzip",
        "hashlib",
        "heapq",
        "hmac",
        "html",
        "http",
        "importlib",
        "inspect",
        "io",
        "ipaddress",
        "itertools",
        "json",
        "logging",
        "math",
        "mimetypes",
        "multiprocessing",
        "numbers",
        "operator",
        "os",
        "pathlib",
        "pickle",
        "platform",
        "plistlib",
        "pprint",
        "queue",
        "random",
        "re",
        "secrets",
        "select",
        "shlex",
        "shutil",
        "signal",
        "socket",
        "sqlite3",
        "ssl",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "timeit",
        "tkinter",
        "traceback",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "weakref",
        "webbrowser",
        "xml",
        "zipfile",
        "io",
    }


def import_is_available(module_name):

    try:
        __import__(module_name)
        return True

    except Exception:
        return False


# =========================================================
# INSTALL SOURCE DEPENDENCIES
# =========================================================

def install_missing_source_dependencies(source):

    imports = extract_imports_from_source(
        source
    )

    if not imports:
        return True

    missing = []

    for module in sorted(imports):

        if is_standard_library_module(
            module
        ):
            continue

        if import_is_available(
            module
        ):
            continue

        missing.append(module)

    if not missing:
        return True

    print(
        "📦 Missing Python dependencies:"
    )

    for module in missing:

        print(
            f"   - {module}"
        )

    success = True

    for module in missing:

        package = IMPORT_TO_PIP.get(
            module,
            module,
        )

        installed = (
            install_python_package(
                package
            )
        )

        if not installed:
            success = False

    return success


# =========================================================
# ERROR -> MISSING MODULE
# =========================================================

def extract_missing_module(error_text):

    text = str(
        error_text or ""
    )

    patterns = [
        r"No module named ['\"]([^'\"]+)['\"]",
        r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            module = (
                match.group(1)
                .split(".")[0]
                .strip()
            )

            if re.fullmatch(
                r"[A-Za-z0-9_-]+",
                module,
            ):
                return module

    return None


def install_missing_runtime_dependency(
    error_text
):

    module = extract_missing_module(
        error_text
    )

    if not module:
        return False

    package = IMPORT_TO_PIP.get(
        module,
        module,
    )

    print(
        f"📦 Runtime dependency missing: "
        f"{module}"
    )

    return install_python_package(
        package
    )


# =========================================================
# GENERATE PYTHON
# =========================================================

def generate_python_fallback(
    user_request
):

    deterministic = (
        deterministic_python_source(
            user_request
        )
    )

    if deterministic:
        return deterministic, None

    prompt = f"""
Write a COMPLETE executable Python program for this request:

USER REQUEST:

{user_request}

Requirements:

- Return ONLY Python source.
- No Markdown.
- No code fences.
- No explanation.
- Actually perform the requested task.
- No placeholders.
- No TODO.
- Windows computer.
- Third-party packages ARE allowed.
- Missing packages will automatically be installed.
- Do not avoid packages because they may not be installed.
- Do not use Linux paths.
- Do not use /home.
- Do not use /media.
- Print the useful final result.
"""

    last_error = None

    for attempt in range(
        PYTHON_GENERATION_ATTEMPTS
    ):

        try:

            response = ollama.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert "
                            "Windows Python programmer. "
                            "Return only complete "
                            "executable Python source."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                think=False,
                options={
                    "temperature": 0.0,
                    "num_ctx": 8192,
                    "num_predict": 4096,
                },
            )

            code = clean_generated_code(
                response.message.content
                or ""
            )

            valid, error = (
                validate_generated_python(
                    code
                )
            )

            if valid:
                return code, None

            last_error = error

            prompt += f"""

The previous code was rejected:

{error}

Generate a complete real implementation.
"""

        except Exception as e:

            last_error = str(e)

    return (
        None,
        "ERROR: Could not generate valid Python: "
        + str(last_error),
    )


# =========================================================
# CREATE / UPDATE FILE
# =========================================================

def create_or_update_python_file(
    filename,
    code,
):

    safe_path = normalize_project_path(
        filename
    )

    if not safe_path:
        return (
            "ERROR: Python file must be inside "
            "the project directory."
        )

    full_path = (
        PROJECT_DIR / safe_path
    )

    try:

        if full_path.exists():

            print(
                f"📄 Updating existing Python file: "
                f"{safe_path}"
            )

            result = write_code_file(
                path=safe_path,
                content=code,
            )

        else:

            print(
                f"📄 Creating Python file: "
                f"{safe_path}"
            )

            result = create_code_file(
                path=safe_path,
                content=code,
            )

        print(
            f"📤 Result: {result}"
        )

        return str(result)

    except Exception as e:

        return (
            "ERROR: Could not create/update "
            f"Python file: {e}"
        )


# =========================================================
# EXECUTION OUTPUT
# =========================================================

def extract_stdout(result):

    text = str(
        result or ""
    )

    match = re.search(
        r"STDOUT:\s*(.*?)(?:\n\nSTATUS:|\Z)",
        text,
        re.DOTALL,
    )

    if not match:
        return ""

    return match.group(1).strip()


def extract_stderr(result):

    text = str(
        result or ""
    )

    match = re.search(
        r"STDERR:\s*(.*?)(?:\n\nSTATUS:|\Z)",
        text,
        re.DOTALL,
    )

    if not match:
        return ""

    return match.group(1).strip()


def execution_success(result):

    text = str(
        result or ""
    )

    return (
        "STATUS: SUCCESS"
        in text
        or
        "Exit code: 0"
        in text
    )


# =========================================================
# DIRECT WINDOWS PYTHON EXECUTOR
# =========================================================

def execute_python_process(
    full_path
):

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(full_path),
            ],
            cwd=str(
                PROJECT_DIR
            ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode == 0:

            return (
                True,
                stdout.strip(),
                stderr.strip(),
                result.returncode,
            )

        combined = (
            stdout
            + "\n"
            + stderr
        ).strip()

        return (
            False,
            stdout.strip(),
            combined,
            result.returncode,
        )

    except subprocess.TimeoutExpired as e:

        stdout = (
            e.stdout
            if isinstance(
                e.stdout,
                str,
            )
            else ""
        )

        stderr = (
            e.stderr
            if isinstance(
                e.stderr,
                str,
            )
            else ""
        )

        return (
            False,
            stdout,
            "Python execution timed out.\n"
            + stderr,
            -1,
        )

    except Exception as e:

        return (
            False,
            "",
            f"Python execution error: {e}",
            -1,
        )


# =========================================================
# SAFE PYTHON RUNNER
# =========================================================

def run_python_safe(path):

    safe_path = normalize_project_path(
        path
    )

    if not safe_path:
        return (
            "ERROR: Python path must be inside "
            "the project directory."
        )

    if not safe_path.lower().endswith(
        ".py"
    ):
        return (
            "ERROR: run_python_file requires "
            "a .py file."
        )

    full_path = (
        PROJECT_DIR / safe_path
    )

    if not full_path.exists():
        return (
            "ERROR: Python file does not exist: "
            f"{safe_path}"
        )

    try:

        source_result = read_code_file(
            path=safe_path
        )

        source = str(
            source_result
        )

        if source.startswith(
            "ERROR:"
        ):
            return source

    except Exception as e:

        return (
            "ERROR: Could not read Python source: "
            f"{e}"
        )

    print(
        "📦 Checking Python dependencies "
        "before execution..."
    )

    install_missing_source_dependencies(
        source
    )

    last_error = ""

    for attempt in range(
        PYTHON_EXECUTION_ATTEMPTS
    ):

        print(
            f"▶️ Running Python file: "
            f"{safe_path} "
            f"(attempt {attempt + 1}/"
            f"{PYTHON_EXECUTION_ATTEMPTS})"
        )

        success, stdout, stderr, code = (
            execute_python_process(
                full_path
            )
        )

        if success:

            print(
                "📤 Python execution succeeded."
            )

            if stdout:
                return stdout

            return "Done."

        last_error = (
            stderr
            or stdout
            or f"Python exited with code {code}"
        )

        print(
            "📤 Python execution failed:"
        )

        print(
            last_error
        )

        missing_module = (
            extract_missing_module(
                last_error
            )
        )

        if missing_module:

            package = IMPORT_TO_PIP.get(
                missing_module,
                missing_module,
            )

            print(
                f"📦 Automatically installing "
                f"missing package: {package}"
            )

            installed = (
                install_python_package(
                    package
                )
            )

            if installed:

                print(
                    "🔄 Package installed. "
                    "Retrying Python..."
                )

                continue

            return (
                "ERROR: Required Python package "
                f"'{package}' could not be installed.\n\n"
                f"{last_error}"
            )

        return (
            "ERROR: Python execution failed.\n\n"
            + last_error
        )

    return (
        "ERROR: Python execution failed after "
        f"{PYTHON_EXECUTION_ATTEMPTS} attempts.\n\n"
        + last_error
    )


# =========================================================
# REPAIR
# =========================================================

def repair_python_script(
    user_request,
    filename,
    source,
    execution_error,
):

    deterministic = (
        deterministic_python_source(
            user_request
        )
    )

    if deterministic:
        return deterministic, None

    prompt = f"""
Repair this Python program.

USER REQUEST:

{user_request}

FILE:

{filename}

CURRENT SOURCE:

{source}

EXECUTION ERROR:

{execution_error}

Return the COMPLETE corrected Python program.

Requirements:

- Return ONLY Python source.
- No Markdown.
- No code fences.
- No explanation.
- Windows compatible.
- Third-party packages are allowed.
- Missing packages are automatically installed.
- Actually complete the user's request.
- Print the useful final result.
"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Windows "
                        "Python debugger. Return only "
                        "complete executable Python "
                        "source."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            think=False,
            options={
                "temperature": 0.0,
                "num_ctx": 8192,
                "num_predict": 4096,
            },
        )

        fixed_code = clean_generated_code(
            response.message.content
            or ""
        )

        valid, error = (
            validate_generated_python(
                fixed_code
            )
        )

        if not valid:
            return None, error

        return fixed_code, None

    except Exception as e:

        return (
            None,
            f"ERROR: Could not generate repair: {e}",
        )


# =========================================================
# COMPLETE PYTHON WORKFLOW
# =========================================================

def execute_python_fallback(
    user_request
):

    global LAST_CODE_FILE

    code, error = (
        generate_python_fallback(
            user_request
        )
    )

    if error:
        return error

    filename = choose_python_filename(
        user_request
    )

    LAST_CODE_FILE = filename

    write_result = (
        create_or_update_python_file(
            filename,
            code,
        )
    )

    if str(
        write_result
    ).startswith("ERROR:"):

        return write_result

    result = run_python_safe(
        filename
    )

    if not str(
        result
    ).startswith("ERROR:"):

        return result

    for attempt in range(
        PYTHON_REPAIR_ATTEMPTS
    ):

        print(
            f"🔧 Python repair attempt "
            f"{attempt + 1}/"
            f"{PYTHON_REPAIR_ATTEMPTS}"
        )

        try:

            source = read_code_file(
                path=filename
            )

        except Exception as e:

            return (
                "ERROR: Could not inspect "
                f"failed Python file: {e}"
            )

        source_text = str(
            source
        )

        if source_text.startswith(
            "ERROR:"
        ):
            return source_text

        fixed_code, repair_error = (
            repair_python_script(
                user_request,
                filename,
                source_text,
                result,
            )
        )

        if repair_error:

            print(
                f"⚠️ Repair generation failed: "
                f"{repair_error}"
            )

            continue

        try:

            write_result = (
                write_code_file(
                    path=filename,
                    content=fixed_code,
                )
            )

        except Exception as e:

            print(
                f"❌ Could not write repaired "
                f"script: {e}"
            )

            continue

        print(
            f"📤 Repair result: "
            f"{write_result}"
        )

        if str(
            write_result
        ).startswith("ERROR:"):

            continue

        result = run_python_safe(
            filename
        )

        if not str(
            result
        ).startswith("ERROR:"):

            return result

    return result


# =========================================================
# EXPLICIT FILE REQUESTS
# =========================================================

def detect_explicit_file_request(
    text
):

    lower = normalize_text(
        text
    ).lower()

    patterns = [
        r"\bcreate\b.*\.py\b",
        r"\bmake\b.*\.py\b",
        r"\bwrite\b.*\.py\b",
        r"\bcreate\b.*\bfile\b",
        r"\bmake\b.*\bfile\b",
        r"\bwrite\b.*\bfile\b",
        r"\bcreate\b.*\bscript\b",
        r"\bmake\b.*\bscript\b",
    ]

    return any(
        re.search(
            pattern,
            lower,
        )
        for pattern in patterns
    )


def extract_file_path(text):

    patterns = [
        r"\bcalled\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",
        r"\bnamed\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",
        r"\bfile\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",
        r"\b([A-Za-z0-9_.-]+\.py)\b",
        r"\b([A-Za-z0-9_.-]+\.js)\b",
        r"\b([A-Za-z0-9_.-]+\.ts)\b",
        r"\b([A-Za-z0-9_.-]+\.ps1)\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None


def wants_run_after_create(
    text
):

    lower = normalize_text(
        text
    ).lower()

    return (
        (
            "create" in lower
            or "make" in lower
            or "write" in lower
        )
        and
        (
            "run" in lower
            or "execute" in lower
        )
    )


# =========================================================
# UNCLEAR
# =========================================================

def is_unclear_request(text):

    text = normalize_text(
        text
    ).lower()

    if not text:
        return True

    unclear = {
        "how about this",
        "how about that",
        "what about this",
        "what about that",
        "okay",
        "ok",
        "yes",
        "no",
        "do it",
        "try this",
        "try that",
        "continue",
        "go ahead",
        "like this",
        "like that",
        "what now",
    }

    return text in unclear


# =========================================================
# SPECIAL TOOLS
# =========================================================

def get_specialised_tools(
    user_text
):

    lower = user_text.lower()

    selected = []

    if any(
        word in lower
        for word in [
            "search the web",
            "search online",
            "google",
            "look this up online",
            "find online",
            "search for",
        ]
    ):
        selected.append(
            web_search
        )

    if (
        "youtube" in lower
        or "youtube video" in lower
    ):
        selected.append(
            youtube_search
        )

    if (
        "play music" in lower
        or "play song" in lower
        or "spotify" in lower
    ):
        selected.append(
            spotify_play
        )

    if (
        "open " in lower
        or "launch " in lower
        or "start " in lower
    ):
        selected.append(
            open_application
        )

    unique = []

    for tool in selected:

        if tool not in unique:
            unique.append(tool)

    return unique


# =========================================================
# TOOL VALIDATION
# =========================================================

def validate_tool_call(
    name,
    arguments,
):

    arguments = arguments or {}

    if name in {
        "create_code_file",
        "read_code_file",
        "write_code_file",
        "open_code_in_vscode",
        "run_python_file",
    }:

        path = str(
            arguments.get(
                "path",
                "",
            )
        ).strip()

        if not normalize_project_path(
            path
        ):

            return (
                False,
                "ERROR: This tool only accepts "
                "paths inside the project directory.",
            )

    if name == "run_python_file":

        path = str(
            arguments.get(
                "path",
                "",
            )
        ).strip()

        if not path.lower().endswith(
            ".py"
        ):

            return (
                False,
                "ERROR: run_python_file requires "
                "a .py file.",
            )

    return True, None


# =========================================================
# TOOL FAILURE
# =========================================================

def tool_failure_message(
    name,
    arguments,
    result,
):

    try:

        formatted_arguments = (
            json.dumps(
                arguments,
                indent=2,
            )
        )

    except Exception:

        formatted_arguments = str(
            arguments
        )

    return f"""
TOOL FAILURE.

Tool:

{name}

Arguments:

{formatted_arguments}

Result:

{result}

Do not repeat the exact same failed call.

If Python can complete the request, generate a complete
Python program and use the controller's Python workflow.
"""


# =========================================================
# TEXTUAL TOOL CALL
# =========================================================

def parse_textual_tool_call(
    text
):

    if not text:
        return None

    text = text.strip()

    try:

        data = json.loads(
            text
        )

        if isinstance(
            data,
            dict,
        ):

            name = (
                data.get("name")
                or data.get("tool")
                or data.get("function")
            )

            arguments = (
                data.get("arguments")
                or data.get("args")
                or {}
            )

            if name:
                return name, arguments

    except Exception:
        pass

    match = re.search(
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,'
        r'\s*"arguments"\s*:\s*(\{.*\})\s*\}',
        text,
        re.DOTALL,
    )

    if match:

        name = match.group(1)

        try:

            arguments = json.loads(
                match.group(2)
            )

        except Exception:

            arguments = {}

        return name, arguments

    return None


# =========================================================
# PENDING INSTALLATION CONFIRMATION
# =========================================================

def is_yes_response(text):
    text = normalize_text(text).lower()

    return text in {
        "yes",
        "y",
        "כן",
        "כן בבקשה",
        "כן תתקין",
        "תתקין",
        "תתקיני",
        "בוודאי",
        "בטח",
        "sure",
        "ok",
        "okay",
        "go ahead",
        "do it",
    }


def is_no_response(text):
    text = normalize_text(text).lower()

    return text in {
        "no",
        "n",
        "לא",
        "לא תודה",
        "אל תתקין",
        "אל תתקיני",
        "ביטול",
        "cancel",
        "don't",
        "do not",
    }


# =========================================================
# PENDING INSTALLATION CONFIRMATION
# =========================================================

PENDING_INSTALLATION = None


def is_yes_response(text):

    text = normalize_text(
        text
    ).lower()

    return text in {
        "yes",
        "y",
        "כן",
        "כן בבקשה",
        "כן תתקין",
        "תתקין",
        "תתקיני",
        "בוודאי",
        "בטח",
        "sure",
        "ok",
        "okay",
        "go ahead",
        "do it",
    }


def is_no_response(text):

    text = normalize_text(
        text
    ).lower()

    return text in {
        "no",
        "n",
        "לא",
        "לא תודה",
        "אל תתקין",
        "אל תתקיני",
        "ביטול",
        "cancel",
        "don't",
        "do not",
    }

def install_application_after_confirmation(
    application,
    original_arguments=None,
):
    """
    Internal installation path.

    This function is NOT exposed to Ollama.
    It can only be called after the user explicitly
    confirms the installation.
    """

    application = normalize_application_name(
        application
    )

    if not application:
        return (
            "ERROR: No application was specified."
        )

    original_arguments = (
        original_arguments or {}
    )

    safe_kwargs = dict(
        original_arguments
    )

    # Never allow the AI-generated arguments to
    # control the confirmation mechanism.
    safe_kwargs.pop(
        "confirm_install",
        None,
    )

    safe_kwargs.pop(
        "install",
        None,
    )

    print(
        f"📦 Approved installation: {application}"
    )

    try:

        result = raw_open_application(
            application=application,
            confirm_install=True,
            install=True,
            **safe_kwargs,
        )

        return str(
            result or ""
        ).strip()

    except TypeError:

        # Compatibility with older versions of
        # raw_open_application.

        try:

            result = raw_open_application(
                application=application,
                confirm_install=True,
                **safe_kwargs,
            )

            return str(
                result or ""
            ).strip()

        except TypeError:

            try:

                result = raw_open_application(
                    application=application,
                    install=True,
                    **safe_kwargs,
                )

                return str(
                    result or ""
                ).strip()

            except Exception as e:

                return (
                    "ERROR: Installation failed: "
                    f"{e}"
                )

        except Exception as e:

            return (
                "ERROR: Installation failed: "
                f"{e}"
            )

    except Exception as e:

        return (
            "ERROR: Installation failed: "
            f"{e}"
        )

def handle_pending_installation(text):

    global PENDING_INSTALLATION

    if PENDING_INSTALLATION is None:
        return None

    # =====================================================
    # YES
    # =====================================================

    if is_yes_response(text):

        pending = dict(
            PENDING_INSTALLATION
        )

        application = pending.get(
            "application"
        )

        original_arguments = pending.get(
            "original_arguments",
            {},
        )

        if not application:

            PENDING_INSTALLATION = None

            return (
                "I couldn't determine which "
                "application to install."
            )

        print(
            "✅ User explicitly approved installation."
        )

        print(
            f"📦 Application: {application}"
        )

        print(
            "📦 Starting installation..."
        )

        # IMPORTANT:
        #
        # Do NOT call open_application() here.
        #
        # open_application() is the protected wrapper
        # that refuses AI-generated installation requests.
        #
        # We call the internal installation function because
        # the user has explicitly confirmed with YES.

        result = install_application_after_confirmation(
            application=application,
            original_arguments=original_arguments,
        )

        result_text = str(
            result or ""
        ).strip()

        print(
            f"📤 Installation result: "
            f"{result_text}"
        )

        # =================================================
        # STILL REQUIRES CONFIRMATION
        # =================================================

        if result_text.startswith(
            "INSTALL_CONFIRMATION_REQUIRED:"
        ):

            confirmation_text = (
                result_text.split(
                    ":",
                    1,
                )[1].strip()
            )

            PENDING_INSTALLATION = pending

            return confirmation_text

        # =================================================
        # FAILED
        # =================================================

        if result_text.startswith(
            "ERROR:"
        ):

            # Keep pending so the user can retry.
            PENDING_INSTALLATION = pending

            return result_text

        # =================================================
        # SUCCESS
        # =================================================

        PENDING_INSTALLATION = None

        return result_text or (
            f"{application} was installed successfully."
        )

    # =====================================================
    # NO
    # =====================================================

    if is_no_response(text):

        application = (
            PENDING_INSTALLATION.get(
                "application",
                "the application",
            )
        )

        print(
            f"❌ User declined installation "
            f"of {application}."
        )

        PENDING_INSTALLATION = None

        return (
            f"Okay, I won't install "
            f"{application}."
        )

    # =====================================================
    # UNKNOWN ANSWER
    # =====================================================

    return (
        "Please answer yes or no. "
        "Would you like me to install it?"
    )

# =========================================================
# MAIN AGENT
# =========================================================

def run_agent(user_text):

    global LAST_CODE_FILE
    global PENDING_INSTALLATION

    user_text = normalize_text(
        user_text
    )

    if not user_text:
        return (
            "I didn't receive a request."
        )

    # =====================================================
    # PENDING INSTALLATION
    #
    # אם יש התקנה שממתינה לאישור:
    #
    # NEVER send the new message to Ollama.
    #
    # "yes" -> install
    # "no"  -> cancel
    #
    # Any other answer -> ask again.
    # =====================================================

    if PENDING_INSTALLATION is not None:

        print(
            "📦 Pending installation detected."
        )

        pending_result = (
            handle_pending_installation(
                user_text
            )
        )

        if pending_result is not None:

            print(
                f"📤 Pending installation result: "
                f"{pending_result}"
            )

            return pending_result

    # =====================================================
    # UNCLEAR REQUEST
    # =====================================================

    if is_unclear_request(
        user_text
    ):

        return (
            "What would you like me to do?"
        )

    print(
        "🧠 Sending request to JARVIS Agent..."
    )

    # =====================================================
    # MEMORY
    # =====================================================

    memory_result = handle_memory(
        user_text
    )

    if memory_result:
        return memory_result

    # =====================================================
    # LOCAL SYSTEM REQUEST
    #
    # CRITICAL:
    #
    # This happens BEFORE Ollama.
    #
    # Therefore:
    #
    # "list services"
    #
    # can NEVER be sent to Qwen to invent psutil code.
    # =====================================================

    print(
        "🔍 DEBUG services request:",
        is_services_request(user_text),
    )

    print(
        "🔍 DEBUG system request:",
        is_system_request(user_text),
    )

    if is_system_request(
        user_text
    ):

        print(
            "🧰 Local system operation detected."
        )

        print(
            "🧰 Using deterministic Windows/Python execution."
        )

        return execute_python_fallback(
            user_text
        )

    # =====================================================
    # FILE CREATION
    # =====================================================

    if detect_explicit_file_request(
        user_text
    ):

        filename = extract_file_path(
            user_text
        )

        if not filename:

            return (
                "What would you like me to "
                "name the file?"
            )

        filename = normalize_project_path(
            filename
        )

        if not filename:

            return (
                "The file must be inside the "
                "project directory."
            )

        code, error = (
            generate_python_fallback(
                user_text
            )
        )

        if error:
            return error

        result = (
            create_or_update_python_file(
                filename,
                code,
            )
        )

        if result.startswith(
            "ERROR:"
        ):
            return result

        LAST_CODE_FILE = filename

        if wants_run_after_create(
            user_text
        ):

            return run_python_safe(
                filename
            )

        return (
            f"Created {filename} successfully."
        )

    # =====================================================
    # SPECIALISED TOOLS
    # =====================================================

    selected_tools = (
        get_specialised_tools(
            user_text
        )
    )

    if not selected_tools:

        print(
            "🧰 No specialised tool directly matches."
        )

        print(
            "🧰 Generating executable Python."
        )

        return execute_python_fallback(
            user_text
        )

    print(
        "🧰 Tools available: "
        + ", ".join(
            getattr(
                tool,
                "__name__",
                str(tool),
            )
            for tool in selected_tools
        )
    )

    # =====================================================
    # OLLAMA AGENT
    # =====================================================

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_text,
        },
    ]

    for step in range(
        MAX_AGENT_STEPS
    ):

        # =================================================
        # ABSOLUTE SAFETY CHECK
        #
        # If a previous tool requested installation
        # confirmation, NEVER continue the agent.
        # =================================================

        if PENDING_INSTALLATION is not None:

            print(
                "⛔ Installation confirmation is pending."
            )

            print(
                "⛔ Stopping Ollama agent immediately."
            )

            application = (
                PENDING_INSTALLATION.get(
                    "application",
                    "the application",
                )
            )

            return (
                f"{application} isn't installed. "
                "Would you like me to install it?"
            )

        print(
            f"🧠 Agent step "
            f"{step + 1}/"
            f"{MAX_AGENT_STEPS}"
        )

        try:

            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=selected_tools,
                think=False,
                options={
                    "temperature": 0.0,
                    "num_ctx": 8192,
                    "num_predict": 2048,
                },
            )

        except Exception as e:

            return (
                "I was unable to communicate "
                "with the local AI model: "
                f"{e}"
            )

        messages.append(
            response.message
        )

        tool_calls = (
            response.message.tool_calls
            or []
        )

        # =================================================
        # NO TOOL CALL
        # =================================================

        if not tool_calls:

            answer = (
                response.message.content
                or ""
            ).strip()

            parsed = (
                parse_textual_tool_call(
                    answer
                )
            )

            # =============================================
            # TEXTUAL TOOL CALL
            # =============================================

            if parsed:

                name, arguments = parsed

                function = (
                    AVAILABLE_FUNCTIONS.get(
                        name
                    )
                )

                allowed = any(
                    getattr(
                        tool,
                        "__name__",
                        "",
                    ) == name
                    for tool in selected_tools
                )

                if (
                    not allowed
                    or function is None
                ):

                    return (
                        execute_python_fallback(
                            user_text
                        )
                    )

                valid, error = (
                    validate_tool_call(
                        name,
                        arguments,
                    )
                )

                if not valid:

                    messages.append({
                        "role": "tool",
                        "content":
                            tool_failure_message(
                                name,
                                arguments,
                                error,
                            ),
                    })

                    continue

                try:

                    result = function(
                        **arguments
                    )

                except Exception as e:

                    result = (
                        "ERROR: Tool execution "
                        f"failed: {e}"
                    )

                print(
                    f"📤 Result: {result}"
                )

                result_text = str(
                    result
                ).strip()

                # =========================================
                # INSTALLATION CONFIRMATION
                #
                # CRITICAL:
                #
                # As soon as the tool says:
                #
                # INSTALL_CONFIRMATION_REQUIRED:
                #
                # STOP EVERYTHING.
                #
                # Do NOT:
                #
                # - call Ollama again
                # - generate Python
                # - create python_task.py
                # - execute anything
                #
                # Save the pending installation and return
                # the question directly to the user.
                # =========================================

                if result_text.startswith(
                    "INSTALL_CONFIRMATION_REQUIRED:"
                ):

                    application = (
                        arguments.get(
                            "application"
                        )
                    )

                    package_id = (
                        arguments.get(
                            "package_id"
                        )
                    )

                    # -------------------------------------
                    # SAVE PENDING INSTALLATION
                    # -------------------------------------

                    PENDING_INSTALLATION = {
                        "application": application,
                        "package_id": package_id,
                        "original_arguments": dict(
                            arguments
                        ),
                    }

                    confirmation_text = (
                        result_text.split(
                            ":",
                            1,
                        )[1].strip()
                    )

                    print(
                        "⛔ INSTALLATION REQUIRES USER CONFIRMATION."
                    )

                    print(
                        f"📦 Application: {application}"
                    )

                    print(
                        f"📦 Package ID: {package_id}"
                    )

                    print(
                        f"❓ {confirmation_text}"
                    )

                    # -------------------------------------
                    # ABSOLUTELY IMPORTANT:
                    #
                    # RETURN HERE.
                    #
                    # Do not continue the for loop.
                    # Do not call Ollama again.
                    # Do not generate Python.
                    # -------------------------------------

                    return confirmation_text

                # =========================================
                # NORMAL ERROR
                # =========================================

                if result_text.startswith(
                    "ERROR:"
                ):

                    messages.append({
                        "role": "tool",
                        "content":
                            tool_failure_message(
                                name,
                                arguments,
                                result_text,
                            ),
                    })

                    continue

                # =========================================
                # NORMAL TOOL SUCCESS
                # =========================================

                messages.append({
                    "role": "tool",
                    "content": result_text,
                })

                continue

            # =============================================
            # NORMAL TEXT ANSWER
            # =============================================

            answer = remove_thinking(
                answer
            )

            if not answer:

                # -----------------------------------------
                # NEVER FALL BACK TO PYTHON IF INSTALLATION
                # IS WAITING FOR CONFIRMATION.
                # -----------------------------------------

                if PENDING_INSTALLATION is not None:

                    application = (
                        PENDING_INSTALLATION.get(
                            "application",
                            "the application",
                        )
                    )

                    return (
                        f"{application} isn't installed. "
                        "Would you like me to install it?"
                    )

                return (
                    execute_python_fallback(
                        user_text
                    )
                )

            return answer

        # =================================================
        # TOOL CALLS
        # =================================================

        for call in tool_calls:

            # ---------------------------------------------
            # SAFETY:
            #
            # If another tool call somehow created a
            # pending installation, stop processing any
            # additional tool calls immediately.
            # ---------------------------------------------

            if PENDING_INSTALLATION is not None:

                application = (
                    PENDING_INSTALLATION.get(
                        "application",
                        "the application",
                    )
                )

                print(
                    "⛔ Stopping remaining tool calls "
                    "because installation confirmation "
                    "is pending."
                )

                return (
                    f"{application} isn't installed. "
                    "Would you like me to install it?"
                )

            name = call.function.name

            arguments = (
                call.function.arguments
            )

            if isinstance(
                arguments,
                str,
            ):

                try:

                    arguments = json.loads(
                        arguments
                    )

                except Exception:

                    arguments = {}

            if not isinstance(
                arguments,
                dict,
            ):

                arguments = {}

            print(
                f"🔧 Tool: {name}"
            )

            print(
                f"📦 Arguments: {arguments}"
            )

            # =============================================
            # TOOL AVAILABILITY
            # =============================================

            allowed = any(
                getattr(
                    tool,
                    "__name__",
                    "",
                ) == name
                for tool in selected_tools
            )

            if not allowed:

                result = (
                    "ERROR: Tool is not "
                    "available for this request."
                )

                messages.append({
                    "role": "tool",
                    "content":
                        tool_failure_message(
                            name,
                            arguments,
                            result,
                        ),
                })

                continue

            # =============================================
            # GET FUNCTION
            # =============================================

            function = (
                AVAILABLE_FUNCTIONS.get(
                    name
                )
            )

            if function is None:

                result = (
                    f"ERROR: Unknown tool {name}"
                )

                messages.append({
                    "role": "tool",
                    "content":
                        tool_failure_message(
                            name,
                            arguments,
                            result,
                        ),
                })

                continue

            # =============================================
            # VALIDATE TOOL
            # =============================================

            valid, validation_error = (
                validate_tool_call(
                    name,
                    arguments,
                )
            )

            if not valid:

                messages.append({
                    "role": "tool",
                    "content":
                        tool_failure_message(
                            name,
                            arguments,
                            validation_error,
                        ),
                })

                continue

            # =============================================
            # PYTHON TOOL
            #
            # Always route through our safe executor.
            # =============================================

            if name == "run_python_file":

                path = str(
                    arguments.get(
                        "path",
                        "",
                    )
                ).strip()

                if not project_file_exists(
                    path
                ):

                    result = (
                        "ERROR: Python file does "
                        f"not exist: {path}"
                    )

                    messages.append({
                        "role": "tool",
                        "content":
                            tool_failure_message(
                                name,
                                arguments,
                                result,
                            ),
                    })

                    continue

                result = run_python_safe(
                    path
                )

                if not str(
                    result
                ).startswith("ERROR:"):

                    return result

                messages.append({
                    "role": "tool",
                    "content":
                        tool_failure_message(
                            name,
                            arguments,
                            result,
                        ),
                })

                continue

            # =============================================
            # NORMAL TOOL EXECUTION
            # =============================================

            try:

                result = function(
                    **arguments
                )

            except Exception as e:

                result = (
                    "ERROR: Tool execution "
                    f"failed: {e}"
                )

            print(
                f"📤 Result: {result}"
            )

            result_text = str(
                result
            ).strip()

            # =============================================
            # INSTALLATION CONFIRMATION
            #
            # THIS IS THE CRITICAL FIX.
            #
            # The moment open_application returns:
            #
            # INSTALL_CONFIRMATION_REQUIRED:
            #
            # we save the request and RETURN.
            #
            # There is NO second Ollama step.
            #
            # There is NO Python fallback.
            #
            # There is NO python_task.py.
            # =============================================

            if result_text.startswith(
                "INSTALL_CONFIRMATION_REQUIRED:"
            ):

                application = (
                    arguments.get(
                        "application"
                    )
                )

                package_id = (
                    arguments.get(
                        "package_id"
                    )
                )

                # -----------------------------------------
                # Save pending installation
                # -----------------------------------------

                PENDING_INSTALLATION = {
                    "application": application,
                    "package_id": package_id,
                    "original_arguments": dict(
                        arguments
                    ),
                }

                confirmation_text = (
                    result_text.split(
                        ":",
                        1,
                    )[1].strip()
                )

                print(
                    ""
                )

                print(
                    "⛔ ========================================"
                )

                print(
                    "⛔ INSTALLATION CONFIRMATION REQUIRED"
                )

                print(
                    "⛔ ========================================"
                )

                print(
                    f"📦 Application: {application}"
                )

                print(
                    f"📦 Package ID: {package_id}"
                )

                print(
                    f"❓ {confirmation_text}"
                )

                print(
                    "⛔ Waiting for user's answer..."
                )

                # -----------------------------------------
                # ABSOLUTE STOP.
                #
                # This return is intentional.
                #
                # The next user message will enter
                # run_agent() again and hit:
                #
                # if PENDING_INSTALLATION:
                #
                # at the very top.
                # -----------------------------------------

                return confirmation_text

            # =============================================
            # NORMAL TOOL ERROR
            # =============================================

            if result_text.startswith(
                "ERROR:"
            ):

                messages.append({
                    "role": "tool",
                    "content":
                        tool_failure_message(
                            name,
                            arguments,
                            result_text,
                        ),
                })

                continue

            # =============================================
            # NORMAL TOOL SUCCESS
            # =============================================

            messages.append({
                "role": "tool",
                "content": result_text,
            })

            # =============================================
            # EXTRA SAFETY CHECK
            #
            # If anything set PENDING_INSTALLATION while
            # processing the tool, immediately stop.
            # =============================================

            if PENDING_INSTALLATION is not None:

                application = (
                    PENDING_INSTALLATION.get(
                        "application",
                        "the application",
                    )
                )

                print(
                    "⛔ Installation is pending."
                )

                return (
                    f"{application} isn't installed. "
                    "Would you like me to install it?"
                )

    # =====================================================
    # AGENT EXHAUSTED
    #
    # IMPORTANT:
    #
    # NEVER generate Python if an installation is pending.
    # =====================================================

    if PENDING_INSTALLATION is not None:

        application = (
            PENDING_INSTALLATION.get(
                "application",
                "the application",
            )
        )

        print(
            "⛔ Agent exhausted while installation "
            "confirmation is pending."
        )

        return (
            f"{application} isn't installed. "
            "Would you like me to install it?"
        )

    print(
        "⏱️ Agent reached maximum steps."
    )

    return execute_python_fallback(
        user_text
    )