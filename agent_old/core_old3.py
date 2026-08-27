import json
import re
import ctypes
import shutil
import socket
import urllib.request
from pathlib import Path

import ollama

from agent.tools import (
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
)


# =========================================================
# SETTINGS
# =========================================================

MODEL = "qwen3:1.7b"

MAX_AGENT_STEPS = 10
PYTHON_REPAIR_ATTEMPTS = 3
PYTHON_GENERATION_ATTEMPTS = 2

PROJECT_DIR = Path.cwd().resolve()

LAST_CODE_FILE = None


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
}


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are JARVIS.

You are a local AI assistant running on Windows.

Your job is to COMPLETE the user's CURRENT request.

IMPORTANT:

When the user asks you to create code, you must actually generate
working executable code.

Do NOT generate placeholders.

Do NOT write things like:

    "X seconds"

    "implement this here"

    "placeholder"

    "TODO"

    "example"

    "return the result here"

The generated program must actually perform the requested operation.

============================================================
PYTHON GENERATION
============================================================

When Python is required:

1. Generate complete Python source.
2. Use the standard library whenever possible.
3. Assume Windows.
4. Do not invent Linux paths.
5. Do not use /home.
6. Do not use /media.
7. Do not create another script.
8. Print the useful final result.
9. Do not return Markdown.
10. Do not return code fences.
11. Do not return explanations.
12. Do not return placeholder values.

The controller, not you, decides whether a file should be
created or updated.

The controller, not you, decides when the Python file should
be executed.

============================================================
LOCAL COMPUTER INFORMATION
============================================================

Local computer operations must use real Windows/Python APIs.

Examples:

- CPU usage
- RAM usage
- disk space
- uptime
- local IP
- public IP
- computer information
- process information

Do not use web search for local computer information.

============================================================
UPTIME
============================================================

Windows uptime must use:

ctypes.windll.kernel32.GetTickCount64()

Do not calculate uptime from the current Python process.

============================================================
FINAL RESPONSE
============================================================

Return only the useful result.

Do not expose:

- tool calls
- internal reasoning
- prompts
- Python source
- debugging
- implementation details

If a program prints:

712.53 GB free of 930.50 GB

return:

712.53 GB free of 930.50 GB
"""


# =========================================================
# TEXT HELPERS
# =========================================================

def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        str(text or "").strip()
    )


def clean_generated_code(code):
    code = str(code or "").strip()

    # Remove <think> blocks if the model emitted them.
    if "<think>" in code:
        if "</think>" in code:
            code = code.split("</think>", 1)[1].strip()
        else:
            code = code.split("<think>", 1)[0].strip()

    # Remove markdown fences.
    code = re.sub(
        r"^```(?:python|py)?\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"\s*```\s*$",
        "",
        code,
    )

    lines = code.splitlines()

    # Some models return:
    #
    # get_uptime.py
    # ============
    # import ...
    #
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

    # Reject Windows absolute paths.
    if re.match(r"^[A-Za-z]:[\\/]", path):
        return None

    # Reject Unix absolute paths.
    if path.startswith("/"):
        return None

    if path.startswith("\\"):
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
            return "I don't have that information stored in my memory."

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
            return "I don't have that information stored in my memory."

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


def is_system_request(text):
    return (
        is_uptime_request(text)
        or is_external_ip_request(text)
        or is_local_ip_request(text)
        or is_disk_space_request(text)
        or is_cpu_request(text)
        or is_memory_usage_request(text)
    )


# =========================================================
# DETERMINISTIC WINDOWS PYTHON
# =========================================================

def deterministic_python_source(user_request):
    """
    These operations are known exactly.
    Do NOT ask the small LLM to invent their implementation.
    """

    # -----------------------------------------------------
    # UPTIME
    # -----------------------------------------------------

    if is_uptime_request(user_request):

        return r'''import ctypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.GetTickCount64.restype = ctypes.c_ulonglong
kernel32.GetTickCount64.argtypes = []

milliseconds = kernel32.GetTickCount64()

total_seconds = milliseconds // 1000

days, remainder = divmod(total_seconds, 86400)
hours, remainder = divmod(remainder, 3600)
minutes, seconds = divmod(remainder, 60)

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

    # -----------------------------------------------------
    # EXTERNAL IP
    # -----------------------------------------------------

    if is_external_ip_request(user_request):

        return r'''import urllib.request

request = urllib.request.Request(
    "https://api.ipify.org",
    headers={"User-Agent": "Jarvis/1.0"},
)

with urllib.request.urlopen(request, timeout=10) as response:
    ip = response.read().decode("utf-8").strip()

print(ip)
'''

    # -----------------------------------------------------
    # LOCAL IP
    # -----------------------------------------------------

    if is_local_ip_request(user_request):

        return r'''import socket

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM,
)

try:
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
finally:
    sock.close()

print(ip)
'''

    # -----------------------------------------------------
    # DISK
    # -----------------------------------------------------

    if is_disk_space_request(user_request):

        return r'''import shutil

total, used, free = shutil.disk_usage("C:\\")

gb = 1024 ** 3

print(
    f"{free / gb:.2f} GB free of {total / gb:.2f} GB"
)
'''

    # -----------------------------------------------------
    # CPU
    #
    # No psutil dependency.
    # Uses Windows performance counter through ctypes.
    # -----------------------------------------------------

    if is_cpu_request(user_request):

        return r'''import ctypes
import time

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

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

time.sleep(0.15)

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

cpu = max(0.0, min(100.0, cpu))

print(f"{cpu:.1f}%")
'''

    # -----------------------------------------------------
    # RAM
    # -----------------------------------------------------

    if is_memory_usage_request(user_request):

        return r'''import ctypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


status = MEMORYSTATUSEX()
status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

if not kernel32.GlobalMemoryStatusEx(
    ctypes.byref(status)
):
    raise ctypes.WinError()

gb = 1024 ** 3

used = status.ullTotalPhys - status.ullAvailPhys

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

    return "python_task.py"


# =========================================================
# PYTHON CODE VALIDATION
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
        return False, "Generated Python source is empty."

    if looks_like_placeholder_code(code):
        return (
            False,
            "Generated Python contains placeholder code.",
        )

    # Compile without executing.
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
# GENERATE PYTHON
# =========================================================

def generate_python_fallback(user_request):
    """
    Generate executable Python for genuinely open-ended tasks.

    Known Windows/system requests are deterministic and never
    reach the LLM.
    """

    deterministic = deterministic_python_source(
        user_request
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
- Do not use placeholder values.
- Do not write "X", "TODO", "placeholder", etc.
- The program must be executable as-is.
- Use the Python standard library whenever possible.
- The computer is Windows.
- Do not invent Linux paths.
- Do not use /home.
- Do not use /media.
- Do not create another Python file.
- Print the useful final result.
- If the request asks to create or modify something,
  actually perform that operation.
"""

    last_error = None

    for attempt in range(PYTHON_GENERATION_ATTEMPTS):

        try:
            response = ollama.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert Python programmer. "
                            "Return only complete executable Python "
                            "source. Never use placeholders."
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
                response.message.content or ""
            )

            valid, error = validate_generated_python(code)

            if valid:
                return code, None

            last_error = error

            prompt += f"""

Your previous response was rejected because:

{error}

Generate a complete real implementation instead.
"""

        except Exception as e:
            last_error = str(e)

    return (
        None,
        "ERROR: Could not generate valid Python: "
        + str(last_error),
    )


# =========================================================
# FILE CREATE / UPDATE
# =========================================================

def create_or_update_python_file(filename, code):
    """
    The controller ALWAYS decides whether to create or update.

    The LLM never gets to make this decision.
    """

    safe_path = normalize_project_path(filename)

    if not safe_path:
        return (
            "ERROR: Python file must be inside "
            "the project directory."
        )

    full_path = PROJECT_DIR / safe_path

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
            "ERROR: Could not create/update Python file: "
            f"{e}"
        )


# =========================================================
# PYTHON EXECUTION
# =========================================================

def extract_stdout(result):
    text = str(result or "")

    match = re.search(
        r"STDOUT:\s*(.*?)(?:\n\nSTATUS:|\Z)",
        text,
        re.DOTALL,
    )

    if not match:
        return ""

    return match.group(1).strip()


def execution_success(result):
    return "STATUS: SUCCESS" in str(result)


def run_python_safe(path):
    safe_path = normalize_project_path(path)

    if not safe_path:
        return (
            "ERROR: Python path must be inside "
            "the project directory."
        )

    if not safe_path.lower().endswith(".py"):
        return (
            "ERROR: run_python_file requires "
            "a .py file."
        )

    full_path = PROJECT_DIR / safe_path

    if not full_path.exists():
        return (
            "ERROR: Python file does not exist: "
            f"{safe_path}"
        )

    print(
        f"▶️ Running Python file: {safe_path}"
    )

    try:
        result = run_python_file(
            path=safe_path,
        )
    except Exception as e:
        return (
            "ERROR: Python execution failed: "
            f"{e}"
        )

    print(
        f"📤 Result: {result}"
    )

    result_text = str(result)

    if execution_success(result_text):

        output = extract_stdout(result_text)

        if output:
            return output

        return "Done."

    return result_text


# =========================================================
# REPAIR PYTHON
# =========================================================

def repair_python_script(
    user_request,
    filename,
    source,
    execution_error,
):
    """
    Repair genuinely generated code.

    Known system requests are regenerated deterministically.
    """

    deterministic = deterministic_python_source(
        user_request
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
- Do not use placeholders.
- Actually complete the user's request.
- Windows compatible.
- Use standard library whenever possible.
- Print the useful final result.
"""

    try:
        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Python debugger. "
                        "Return only complete corrected "
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

        fixed_code = clean_generated_code(
            response.message.content or ""
        )

        valid, error = validate_generated_python(
            fixed_code
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

def execute_python_fallback(user_request):
    """
    THE IMPORTANT PART.

    generate
        ↓
    create/update
        ↓
    run
        ↓
    inspect
        ↓
    repair
        ↓
    run again
    """

    global LAST_CODE_FILE

    code, error = generate_python_fallback(
        user_request
    )

    if error:
        return error

    filename = choose_python_filename(
        user_request
    )

    LAST_CODE_FILE = filename

    # -----------------------------------------------------
    # Write code.
    # -----------------------------------------------------

    write_result = create_or_update_python_file(
        filename,
        code,
    )

    if write_result.startswith("ERROR:"):
        return write_result

    # -----------------------------------------------------
    # Run.
    # -----------------------------------------------------

    result = run_python_safe(
        filename
    )

    if not str(result).startswith("ERROR:"):
        return result

    # -----------------------------------------------------
    # Repair.
    # -----------------------------------------------------

    for attempt in range(
        PYTHON_REPAIR_ATTEMPTS
    ):

        print(
            f"🔧 Python repair attempt "
            f"{attempt + 1}/{PYTHON_REPAIR_ATTEMPTS}"
        )

        try:
            source = read_code_file(
                path=filename
            )
        except Exception as e:
            return (
                "ERROR: Could not inspect failed "
                f"Python file: {e}"
            )

        source_text = str(source)

        if source_text.startswith("ERROR:"):
            return source_text

        fixed_code, repair_error = repair_python_script(
            user_request,
            filename,
            source_text,
            result,
        )

        if repair_error:
            continue

        print(
            f"🔧 Writing repaired script: {filename}"
        )

        try:
            write_result = write_code_file(
                path=filename,
                content=fixed_code,
            )
        except Exception as e:
            return (
                "ERROR: Could not write repaired "
                f"script: {e}"
            )

        print(
            f"📤 Repair result: {write_result}"
        )

        if str(write_result).startswith("ERROR:"):
            continue

        result = run_python_safe(
            filename
        )

        if not str(result).startswith("ERROR:"):
            return result

    return result


# =========================================================
# EXPLICIT FILE REQUESTS
# =========================================================

def detect_explicit_file_request(text):
    lower = normalize_text(text).lower()

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
        re.search(pattern, lower)
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


def wants_run_after_create(text):
    lower = normalize_text(text).lower()

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
# UNCLEAR REQUEST
# =========================================================

def is_unclear_request(text):
    text = normalize_text(text).lower()

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
# TOOL SELECTION
# =========================================================

def get_specialised_tools(user_text):
    lower = user_text.lower()

    selected = []

    # Web ONLY if explicitly requested.

    web_words = [
        "search the web",
        "search online",
        "google",
        "look this up online",
        "find online",
        "search for",
    ]

    if any(
        word in lower
        for word in web_words
    ):
        selected.append(web_search)

    # YouTube.

    if (
        "youtube" in lower
        or "youtube video" in lower
    ):
        selected.append(youtube_search)

    # Spotify.

    if (
        "play music" in lower
        or "play song" in lower
        or "spotify" in lower
    ):
        selected.append(spotify_play)

    # Applications.

    if (
        "open " in lower
        or "launch " in lower
        or "start " in lower
    ):
        selected.append(open_application)

    # Remove duplicates.

    unique = []

    for tool in selected:
        if tool not in unique:
            unique.append(tool)

    return unique


# =========================================================
# TOOL VALIDATION
# =========================================================

def validate_tool_call(name, arguments):
    arguments = arguments or {}

    if name in {
        "create_code_file",
        "read_code_file",
        "write_code_file",
        "open_code_in_vscode",
        "run_python_file",
    }:

        path = str(
            arguments.get("path", "")
        ).strip()

        if not normalize_project_path(path):
            return (
                False,
                "ERROR: This tool only accepts paths "
                "inside the project directory.",
            )

    if name == "run_python_file":

        path = str(
            arguments.get("path", "")
        ).strip()

        if not path.lower().endswith(".py"):
            return (
                False,
                "ERROR: run_python_file requires a .py file.",
            )

        safe = normalize_project_path(path)

        if not safe:
            return (
                False,
                "ERROR: Invalid project Python path.",
            )

        if not (PROJECT_DIR / safe).exists():
            return (
                False,
                f"ERROR: Python file does not exist: {safe}",
            )

    return True, None


# =========================================================
# TOOL FAILURE MESSAGE
# =========================================================

def tool_failure_message(name, arguments, result):
    return f"""
TOOL FAILURE.

Tool:
{name}

Arguments:
{json.dumps(arguments, indent=2)}

Result:
{result}

Do not repeat the exact same failed call.

If Python can complete the request, generate a complete Python
program and use the controller's Python workflow.
"""


# =========================================================
# TEXTUAL TOOL CALL RECOVERY
# =========================================================

def parse_textual_tool_call(text):
    if not text:
        return None

    text = text.strip()

    try:
        data = json.loads(text)

        if isinstance(data, dict):

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
        r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*'
        r'"arguments"\s*:\s*(\{.*\})\s*\}',
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
# MAIN AGENT
# =========================================================

def run_agent(user_text):
    global LAST_CODE_FILE

    user_text = normalize_text(user_text)

    if not user_text:
        return "I didn't receive a request."

    if is_unclear_request(user_text):
        return "What would you like me to do?"

    print(
        "🧠 Sending request to JARVIS Agent..."
    )

    # =====================================================
    # MEMORY
    # =====================================================

    memory_result = handle_memory(user_text)

    if memory_result:
        return memory_result

    # =====================================================
    # SYSTEM OPERATIONS
    #
    # ABSOLUTELY BEFORE OLLAMA.
    #
    # This is the critical fix.
    # =====================================================

    if is_system_request(user_text):

        print(
            "🧰 Local system operation detected."
        )

        print(
            "🧰 Bypassing LLM tool routing."
        )

        return execute_python_fallback(
            user_text
        )

    # =====================================================
    # EXPLICIT FILE CREATION
    # =====================================================

    if detect_explicit_file_request(user_text):

        filename = extract_file_path(user_text)

        if not filename:
            return (
                "What would you like me to name the file?"
            )

        filename = normalize_project_path(filename)

        if not filename:
            return (
                "The file must be inside the "
                "project directory."
            )

        # Generate actual code.

        code, error = generate_python_fallback(
            user_text
        )

        if error:
            return error

        # Controller chooses create/update.

        result = create_or_update_python_file(
            filename,
            code,
        )

        if result.startswith("ERROR:"):
            return result

        LAST_CODE_FILE = filename

        if wants_run_after_create(user_text):
            return run_python_safe(filename)

        return f"Created {filename} successfully."

    # =====================================================
    # SPECIALISED TOOLS
    # =====================================================

    selected_tools = get_specialised_tools(
        user_text
    )

    # =====================================================
    # NO SPECIAL TOOL
    #
    # Let Python/LLM generate actual executable code.
    # =====================================================

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
    # OLLAMA TOOL AGENT
    #
    # Used ONLY for requests that actually have specialised
    # tools.
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

    for step in range(MAX_AGENT_STEPS):

        print(
            f"🧠 Agent step "
            f"{step + 1}/{MAX_AGENT_STEPS}"
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
                f"with the local AI model: {e}"
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

            parsed = parse_textual_tool_call(
                answer
            )

            if parsed:

                name, arguments = parsed

                function = AVAILABLE_FUNCTIONS.get(
                    name
                )

                allowed = any(
                    getattr(
                        tool,
                        "__name__",
                        "",
                    ) == name
                    for tool in selected_tools
                )

                if not allowed or function is None:

                    return execute_python_fallback(
                        user_text
                    )

                valid, error = validate_tool_call(
                    name,
                    arguments,
                )

                if not valid:

                    messages.append({
                        "role": "tool",
                        "content": tool_failure_message(
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
                        "ERROR: Tool execution failed: "
                        f"{e}"
                    )

                print(
                    f"📤 Result: {result}"
                )

                result_text = str(result)

                if result_text.startswith("ERROR:"):

                    messages.append({
                        "role": "tool",
                        "content": tool_failure_message(
                            name,
                            arguments,
                            result_text,
                        ),
                    })

                    continue

                messages.append({
                    "role": "tool",
                    "content": result_text,
                })

                continue

            # Remove thinking.

            if "<think>" in answer:

                if "</think>" in answer:

                    answer = answer.split(
                        "</think>",
                        1,
                    )[1].strip()

            if not answer:
                return execute_python_fallback(
                    user_text
                )

            return answer

        # =================================================
        # REAL TOOL CALLS
        # =================================================

        for call in tool_calls:

            name = call.function.name

            arguments = call.function.arguments

            if isinstance(arguments, str):

                try:
                    arguments = json.loads(
                        arguments
                    )
                except Exception:
                    arguments = {}

            if not isinstance(arguments, dict):
                arguments = {}

            print(
                f"🔧 Tool: {name}"
            )

            print(
                f"📦 Arguments: {arguments}"
            )

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
                    "ERROR: Tool is not available "
                    "for this request."
                )

                messages.append({
                    "role": "tool",
                    "content": tool_failure_message(
                        name,
                        arguments,
                        result,
                    ),
                })

                continue

            function = AVAILABLE_FUNCTIONS.get(
                name
            )

            if function is None:

                result = (
                    f"ERROR: Unknown tool {name}"
                )

                messages.append({
                    "role": "tool",
                    "content": tool_failure_message(
                        name,
                        arguments,
                        result,
                    ),
                })

                continue

            valid, validation_error = validate_tool_call(
                name,
                arguments,
            )

            if not valid:

                print(
                    f"⚠️ Tool blocked: "
                    f"{validation_error}"
                )

                messages.append({
                    "role": "tool",
                    "content": tool_failure_message(
                        name,
                        arguments,
                        validation_error,
                    ),
                })

                continue

            # -------------------------------------------------
            # NEVER let the model run a nonexistent Python file.
            # -------------------------------------------------

            if name == "run_python_file":

                path = str(
                    arguments.get("path", "")
                ).strip()

                if not project_file_exists(path):

                    result = (
                        f"ERROR: Python file does not exist: "
                        f"{path}"
                    )

                    messages.append({
                        "role": "tool",
                        "content": tool_failure_message(
                            name,
                            arguments,
                            result,
                        ),
                    })

                    continue

                result = run_python_safe(path)

                if not str(result).startswith("ERROR:"):
                    return result

                messages.append({
                    "role": "tool",
                    "content": tool_failure_message(
                        name,
                        arguments,
                        result,
                    ),
                })

                continue

            # -------------------------------------------------
            # NORMAL TOOL
            # -------------------------------------------------

            try:

                result = function(
                    **arguments
                )

            except Exception as e:

                result = (
                    "ERROR: Tool execution failed: "
                    f"{e}"
                )

            print(
                f"📤 Result: {result}"
            )

            result_text = str(result)

            if result_text.startswith("ERROR:"):

                messages.append({
                    "role": "tool",
                    "content": tool_failure_message(
                        name,
                        arguments,
                        result_text,
                    ),
                })

                continue

            messages.append({
                "role": "tool",
                "content": result_text,
            })

    # =====================================================
    # AGENT EXHAUSTED
    # =====================================================

    print(
        "⏱️ Agent reached maximum steps."
    )

    # Last-resort actual Python workflow.

    return execute_python_fallback(
        user_text
    )