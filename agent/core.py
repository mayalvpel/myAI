import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import html
import webbrowser

from agent.memory_manager import (
    build_memory_prompt,
)

from agent.memory import (
    handle_memory_command,
    memory_as_text,
)


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = "qwen3:1.7b"

OLLAMA_URL = (
    "http://127.0.0.1:11434/api/chat"
)

MAX_SCRIPT_REPAIR_ATTEMPTS = 3

PROJECT_DIR = Path(__file__).resolve().parent.parent

GENERATED_FILES_DIR = (
    PROJECT_DIR / "generated_files"
)

GENERATED_FILES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LAST_CODE_FILE = None


# =========================================================
# IMPORT TOOLS
# =========================================================

from agent.tools import (
    tool_open_app,
    tool_close_app,
    tool_install_app,
    tool_is_app_installed,
    tool_run_script,
    tool_execute_python,
)


# =========================================================
# PENDING ACTION
# =========================================================

pending_action = None


# =========================================================
# OLLAMA
# =========================================================

def ask_ollama(
    messages,
    temperature=0.1,
):

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": 2048,
        },
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=180,
        ) as response:

            raw = response.read().decode(
                "utf-8",
                errors="replace",
            )

        result = json.loads(raw)

        message = result.get(
            "message",
            {},
        )

        content = message.get(
            "content",
            "",
        )

        return str(
            content or ""
        ).strip()

    except urllib.error.URLError as e:

        raise RuntimeError(
            "Could not connect to Ollama. "
            "Make sure Ollama is running."
        ) from e

    except Exception as e:

        raise RuntimeError(
            f"Ollama request failed: {e}"
        ) from e


# =========================================================
# TEXT
# =========================================================

def clean_text(text):

    return str(
        text or ""
    ).strip()


def normalize_confirmation(text):

    text = clean_text(text).lower()

    text = re.sub(
        r"[^\w\s']",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# =========================================================
# YES / NO
# =========================================================

def is_yes(text):

    normalized = normalize_confirmation(
        text
    )

    patterns = [
        r"\byes\b",
        r"\byeah\b",
        r"\byep\b",
        r"\byup\b",
        r"\bsure\b",
        r"\babsolutely\b",
        r"\bof course\b",
        r"\bgo ahead\b",
        r"\bdo it\b",
        r"\bplease do\b",
        r"\binstall it\b",
        r"\bplease install\b",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


def is_no(text):

    normalized = normalize_confirmation(
        text
    )

    patterns = [
        r"\bno\b",
        r"\bnope\b",
        r"\bnah\b",
        r"\bcancel\b",
        r"\bnever mind\b",
        r"\bnevermind\b",
        r"\bdon't\b",
        r"\bdo not\b",
        r"\bno thanks\b",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


# =========================================================
# APPLICATION NAME
# =========================================================

def extract_app_name(text):

    text = clean_text(text)

    patterns = [
        r"^(?:open|launch|start|run)\s+(?:the\s+)?(.+)$",
        r"^(?:close|quit|exit)\s+(?:the\s+)?(.+)$",
        r"^(?:install)\s+(?:the\s+)?(.+)$",
    ]

    for pattern in patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return match.group(1).strip(
                " .!?,"
            )

    return None


# =========================================================
# APPLICATION COMMAND DETECTION
# =========================================================

def is_open_command(text):

    return bool(
        re.match(
            r"^(open|launch|start)\b",
            clean_text(text),
            re.IGNORECASE,
        )
    )


def is_close_command(text):

    return bool(
        re.match(
            r"^(close|quit|exit)\b",
            clean_text(text),
            re.IGNORECASE,
        )
    )


def is_install_command(text):

    return bool(
        re.match(
            r"^install\b",
            clean_text(text),
            re.IGNORECASE,
        )
    )


# =========================================================
# OPEN APP
# =========================================================

def handle_open_app(app_name):

    global pending_action

    app_name = clean_text(app_name)

    result = tool_open_app(
        app_name
    )

    if (
        isinstance(result, dict)
        and result.get("success")
    ):

        pending_action = None

        return f"I opened {app_name}."

    if (
        isinstance(result, dict)
        and result.get("not_installed")
    ):

        pending_action = {
            "type": "install_app",
            "app_name": app_name,
        }

        return (
            f"{app_name} is not installed "
            "on this computer. "
            "Would you like me to install it?"
        )

    if isinstance(result, dict):

        error = result.get(
            "error",
            "Unknown error.",
        )

    else:

        error = str(result)

    return (
        f"I couldn't open {app_name}. "
        f"{error}"
    )


# =========================================================
# INSTALL APP
# =========================================================

def handle_install_app(app_name):

    global pending_action

    app_name = clean_text(app_name)

    print(
        f"📦 Installing {app_name}..."
    )

    result = tool_install_app(
        app_name
    )

    if not isinstance(result, dict):

        pending_action = None

        return (
            f"I couldn't install {app_name}. "
            f"{result}"
        )

    if not result.get("success"):

        pending_action = None

        return (
            f"I couldn't install {app_name}. "
            f"{result.get('error', '')}"
        )

    pending_action = None

    if result.get("already_installed"):

        open_result = tool_open_app(
            app_name
        )

        if (
            isinstance(open_result, dict)
            and open_result.get("success")
        ):

            return (
                f"{app_name} was already installed "
                "and I opened it."
            )

        return (
            f"{app_name} is already installed, "
            "but I couldn't open it."
        )

    open_result = tool_open_app(
        app_name
    )

    if (
        isinstance(open_result, dict)
        and open_result.get("success")
    ):

        return (
            f"{app_name} was installed successfully "
            "and I opened it."
        )

    return (
        f"{app_name} was installed successfully, "
        "but I couldn't open it yet."
    )


# =========================================================
# CLOSE APP
# =========================================================

def handle_close_app(app_name):

    app_name = clean_text(app_name)

    result = tool_close_app(
        app_name
    )

    if (
        isinstance(result, dict)
        and result.get("success")
    ):

        return f"I closed {app_name}."

    if isinstance(result, dict):

        error = result.get(
            "error",
            "Unknown error.",
        )

    else:

        error = str(result)

    return (
        f"I couldn't close {app_name}. "
        f"{error}"
    )


# =========================================================
# PENDING ACTION
# =========================================================

def handle_pending_action(text):

    global pending_action

    if pending_action is None:
        return None

    if is_yes(text):

        action = pending_action.copy()

        pending_action = None

        if action.get("type") == "install_app":

            return handle_install_app(
                action.get(
                    "app_name",
                    "",
                )
            )

    if is_no(text):

        app_name = pending_action.get(
            "app_name",
            "the application",
        )

        pending_action = None

        return (
            f"Okay. I won't install {app_name}."
        )

    return "I need a yes or no answer."


# =========================================================
# DIRECT APPLICATION COMMANDS
# =========================================================

def try_application_command(text):

    text = clean_text(text)

    if not text:
        return None

    if is_open_command(text):

        app_name = extract_app_name(text)

        if app_name:
            return handle_open_app(
                app_name
            )

    if is_close_command(text):

        app_name = extract_app_name(text)

        if app_name:
            return handle_close_app(
                app_name
            )

    if is_install_command(text):

        app_name = extract_app_name(text)

        if app_name:
            return handle_install_app(
                app_name
            )

    return None


# =========================================================
# SIMPLE COMMANDS
# =========================================================

def handle_simple_commands(text):

    normalized = clean_text(text).lower()

    greetings = {
        "hello",
        "hi",
        "hey",
        "hello jarvis",
        "hi jarvis",
        "hey jarvis",
    }

    if normalized in greetings:

        return (
            "Hello. How can I help you?"
        )

    return None


# =========================================================
# QWEN DECISION PROMPT
# =========================================================

DECISION_SYSTEM_PROMPT = r"""
You are Jarvis, a Windows desktop AI assistant.

You run locally through Ollama.

DO NOT think.
DO NOT provide reasoning.
DO NOT explain.
Return ONLY valid JSON.

Your job is to decide how to handle the user's request.

You have THREE possible modes:

1. answer
2. script
3. file

=========================================================
MODE: answer
=========================================================

Use "answer" for normal conversational questions that do
not require accessing or changing the computer.

Return:

{
  "mode": "answer",
  "answer": "..."
}

=========================================================
MODE: script
=========================================================

Use "script" when Jarvis must EXECUTE an operation on the
Windows computer.

Examples:

- What is my IP address?
- What is my internal IP address?
- What is my public IP address?
- How much free space is on C drive?
- What files are in Downloads?
- How much RAM is being used?
- What CPU am I using?
- Is Chrome running?
- What is today's date on this computer?
- What is the current Windows username?
- Find PDF files in Downloads.
- Create a folder.
- Rename a file.
- Count files.
- Tell me the battery percentage.

The code in "script" MUST be valid Python 3.

The Python script must print the final human-readable answer.

Do not use input().
Do not wait for interaction.
Do not use Markdown fences.

Prefer Python standard library.

For internal IP, prefer:

import socket

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

try:
    sock.connect(("8.8.8.8", 80))
    ip = sock.getsockname()[0]
finally:
    sock.close()

print(ip)

For public IP, urllib.request may be used.

=========================================================
MODE: file
=========================================================

IMPORTANT:

Use "file" when the user asks you to CREATE, WRITE, GENERATE,
SAVE, or PROVIDE a file.

Examples:

- Give me an HTML file.
- Create an HTML landing page.
- Make a CSS file.
- Create a JavaScript file.
- Generate a JSON file.
- Write a Python file.
- Create a text file.
- Make an SVG file.
- Generate a webpage.
- Create a README file.

DO NOT put HTML, CSS, JavaScript, SVG, JSON, or other file
content inside a Python script.

The "file" mode writes the requested content directly to disk.

Return EXACTLY:

{
  "mode": "file",
  "filename": "example.html",
  "content": "complete file contents"
}

The content must be the actual requested file.

For example, for an HTML request:

{
  "mode": "file",
  "filename": "jewelry_landing.html",
  "content": "<!DOCTYPE html>..."
}

Do NOT create Python code whose purpose is to write the HTML.

=========================================================
IMPORTANT DISTINCTION
=========================================================

"Give me an HTML file"

=> mode = file

"Create an HTML page in my project folder"

=> mode = file

"Open the HTML file in Chrome"

=> this may require script or application handling.

"Check something on my computer"

=> mode = script

"Tell me something you already know"

=> mode = answer

=========================================================
INTERNAL IP
=========================================================

If the user says:

"What is my IP address?"

without specifying public IP,

interpret it as INTERNAL/LAN IP.

Do not answer with the public IP.

=========================================================
PYTHON RULES
=========================================================

For script mode:

- Windows
- Python 3
- print final answer
- no input()
- no Markdown fences
- no explanations outside code
- keep scripts short
- use correct Windows path escaping
- use standard library whenever possible
- dependencies are handled by Jarvis

=========================================================
FILE RULES
=========================================================

For file mode:

- Return the actual file content.
- Do not wrap it in Markdown fences.
- Do not create a Python wrapper.
- Choose a sensible filename.
- Preserve the requested format.
- For HTML, return complete HTML.
- For CSS, return complete CSS.
- For JavaScript, return JavaScript.
- For JSON, return valid JSON.
- For SVG, return valid SVG.

=========================================================
OUTPUT
=========================================================

Return ONLY one of these JSON structures:

{
  "mode": "answer",
  "answer": "..."
}

OR

{
  "mode": "script",
  "reason": "short reason",
  "code": "complete Python code"
}

OR

{
  "mode": "file",
  "filename": "filename.ext",
  "content": "complete file contents"
}

No other format.



IMPORTANT WINDOWS HARDWARE RULES:

For CPU information, DO NOT invent WMI monikers.

NEVER use:

wmi.WMI(moniker="WMI/ComputerSystem")

NEVER use:

wmi.WMI(... )["_instance_"]

If WMI is used for CPU information, use the Win32_Processor
class through the normal WMI query:

import wmi

computer = wmi.WMI()

processors = computer.Win32_Processor()

for processor in processors:
    max_speed = processor.MaxClockSpeed
    current_speed = processor.CurrentClockSpeed

Win32_Processor properties:

MaxClockSpeed = maximum processor speed in MHz.

CurrentClockSpeed = current processor speed in MHz.

For a request such as:

"What is my CPU speed?"

prefer this simple script:

import wmi

computer = wmi.WMI()

processors = computer.Win32_Processor()

if processors:
    processor = processors[0]

    current = processor.CurrentClockSpeed
    maximum = processor.MaxClockSpeed

    if current:
        print(
            f"Current CPU speed: {current / 1000:.2f} GHz"
        )

    if maximum:
        print(
            f"Maximum CPU speed: {maximum / 1000:.2f} GHz"
        )
else:
    print("Could not determine CPU speed.")

Do not use ComputerSystem for CPU clock speed.

Do not use arbitrary WMI monikers.

Do not access WMI objects using ["_instance_"].
"""


# =========================================================
# ASK QWEN
# =========================================================

def ask_qwen_for_action(
    user_text,
):
    print(
        "🧠 Asking Qwen..."
    )

    current_memory = memory_as_text()

    system_prompt = (
        DECISION_SYSTEM_PROMPT
        + "\n\n"
        + "=================================================\n"
        + "USER MEMORY\n"
        + "=================================================\n"
        + current_memory
        + "\n\n"
        + "IMPORTANT MEMORY RULES:\n"
        + "- Use stored memories when relevant.\n"
        + "- Do not invent memories.\n"
        + "- Treat stored memories as facts provided by the user.\n"
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_text,
        },
    ]

    response = ask_ollama(
        messages,
        temperature=0.0,
    )

    return parse_qwen_json(
        response
    )


# =========================================================
# PARSE JSON
# =========================================================

def parse_qwen_json(response):

    response = clean_text(response)

    response = re.sub(
        r"^```(?:json)?\s*",
        "",
        response,
        flags=re.IGNORECASE,
    )

    response = re.sub(
        r"\s*```$",
        "",
        response,
        flags=re.IGNORECASE,
    )

    response = response.strip()

    try:

        parsed = json.loads(response)

        if isinstance(parsed, dict):
            return parsed

    except Exception:
        pass

    start = response.find("{")
    end = response.rfind("}")

    if start >= 0 and end > start:

        candidate = response[
            start:end + 1
        ]

        try:

            parsed = json.loads(
                candidate
            )

            if isinstance(parsed, dict):
                return parsed

        except Exception:
            pass

    return {
        "mode": "answer",
        "answer": response,
    }


# =========================================================
# CLEAN PYTHON
# =========================================================

def clean_python_code(code):

    code = str(
        code or ""
    ).strip()

    code = re.sub(
        r"^```python\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"^```\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"\s*```$",
        "",
        code,
        flags=re.IGNORECASE,
    )

    return code.strip()


# =========================================================
# SAVE FILE
# =========================================================

def save_generated_file(
    filename,
    content,
):

    global LAST_CODE_FILE

    filename = Path(
        str(filename or "generated_file.txt")
    ).name

    if not filename:
        filename = "generated_file.txt"

    path = (
        GENERATED_FILES_DIR
        / filename
    )

    # Prevent accidental overwrite collisions
    if path.exists():

        timestamp = int(
            time.time() * 1000
        )

        path = (
            GENERATED_FILES_DIR
            / f"{path.stem}_{timestamp}{path.suffix}"
        )

    path.write_text(
        str(content or ""),
        encoding="utf-8",
    )

    LAST_CODE_FILE = path

    return path


# =========================================================
# HANDLE FILE
# =========================================================

def handle_file_action(action):

    filename = clean_text(
        action.get(
            "filename",
            "generated_file.txt",
        )
    )

    content = action.get(
        "content",
        "",
    )

    if content is None:
        content = ""

    if not isinstance(content, str):
        content = str(content)

    if not content.strip():

        return (
            "Qwen requested a file, "
            "but returned empty content."
        )

    try:

        path = save_generated_file(
            filename,
            content,
        )

    except Exception as e:

        return (
            f"I couldn't create the file: {e}"
        )

    return (
        f"Created the file successfully\n"
    )


# =========================================================
# SCRIPT REPAIR
# =========================================================

SCRIPT_REPAIR_PROMPT = r"""
You are repairing a Python script for a Windows AI assistant.

Return ONLY corrected Python source code.

Requirements:

- Python 3
- Windows
- print the final answer
- no input()
- no Markdown fences
- preserve the original task
- fix the reported error
- use correct Windows path escaping


IMPORTANT WINDOWS WMI RULE:

If the error contains:

OLE error 0x8004100e

and the script uses Python WMI:

DO NOT invent a WMI moniker.

For CPU information, replace the WMI access with:

import wmi

computer = wmi.WMI()

processors = computer.Win32_Processor()

processor = processors[0]

Use:

processor.CurrentClockSpeed

and/or:

processor.MaxClockSpeed

Do NOT use:

wmi.WMI(moniker="WMI/ComputerSystem")

Do NOT use:

wmi.WMI(... )["_instance_"]

Do NOT query ComputerSystem for CPU clock speed.
"""

def validate_python_code(code):
    import ast

    code = clean_python_code(code)

    if not code:
        return {
            "valid": False,
            "error": "Generated Python code is empty.",
        }

    try:
        ast.parse(code)

        return {
            "valid": True,
        }

    except SyntaxError as e:

        return {
            "valid": False,
            "error": f"SyntaxError: {e}",
        }

    except Exception as e:

        return {
            "valid": False,
            "error": str(e),
        }

def repair_script(
    original_code,
    error_text,
    user_request,
):
    """
    Ask Qwen to repair a generated Python script.

    Returns ONLY valid Python source code.
    Returns an empty string if Qwen cannot produce
    syntactically valid Python.
    """

    strict_prompt = r"""
You are Jarvis Python Code Repair Engine.

Your ONLY task is to repair the Python script.

STRICT RULES:

- Return ONLY complete Python 3 source code.
- Do NOT explain anything.
- Do NOT answer the user's question directly.
- Do NOT write "Final answer:".
- Do NOT write "Here is the code:".
- Do NOT use Markdown code fences.
- Do NOT return the output/result of the program.
- Do NOT return natural language outside the Python code.
- The result MUST be valid Python 3 syntax.
- The script MUST perform the original user request.
- The script MUST print the final human-readable result.
- Do NOT use input().
- Do NOT wait for user interaction.
- Preserve the original task.
- Fix the reported error.

IMPORTANT:

If the previous script contains HTML, CSS, or JavaScript,
do NOT place raw HTML/CSS/JavaScript directly into Python.

If HTML must be created by Python, store it inside a valid
Python string and write it to a file.

For example:

html = '''
<html>
<body>
<h1>Hello</h1>
</body>
</html>
'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Created index.html")

The final response must contain ONLY executable Python code.
"""

    messages = [
        {
            "role": "system",
            "content": strict_prompt,
        },
        {
            "role": "user",
            "content": (
                "USER REQUEST:\n"
                f"{user_request}\n\n"
                "CURRENT PYTHON SCRIPT:\n"
                f"{original_code}\n\n"
                "PYTHON ERROR:\n"
                f"{error_text}\n\n"
                "Repair the script.\n"
                "Return ONLY valid Python 3 source code."
            ),
        },
    ]

    # -----------------------------------------------------
    # FIRST REPAIR ATTEMPT
    # -----------------------------------------------------

    try:
        response = ask_ollama(
            messages,
            temperature=0.0,
        )
    except Exception:
        return ""

    repaired = clean_python_code(
        response
    )

    # -----------------------------------------------------
    # VALIDATE FIRST RESPONSE
    # -----------------------------------------------------

    validation = validate_python_code(
        repaired
    )

    if validation.get("valid"):
        return repaired

    # -----------------------------------------------------
    # SECOND STRICT ATTEMPT
    # -----------------------------------------------------

    retry_messages = [
        {
            "role": "system",
            "content": r"""
You are a Python syntax repair engine.

Return ONLY executable Python 3 source code.

NOTHING ELSE.

No explanation.
No natural language.
No "Final answer:".
No "Here is the code:".
No Markdown.
No ```python.
No ```.

The response MUST be valid Python 3 syntax.

The program MUST perform the original user request.

The program MUST print the final human-readable result.

If the previous script contains HTML/CSS/JavaScript,
keep that content inside Python strings.

Fix the reported Python error.
""",
        },
        {
            "role": "user",
            "content": (
                "ORIGINAL USER REQUEST:\n"
                f"{user_request}\n\n"
                "BROKEN PYTHON SCRIPT:\n"
                f"{original_code}\n\n"
                "ERROR:\n"
                f"{error_text}\n\n"
                "INVALID REPAIR:\n"
                f"{repaired}\n\n"
                "Generate the complete corrected Python script."
            ),
        },
    ]

    try:
        retry_response = ask_ollama(
            retry_messages,
            temperature=0.0,
        )
    except Exception:
        return ""

    retry_code = clean_python_code(
        retry_response
    )

    # -----------------------------------------------------
    # VALIDATE SECOND RESPONSE
    # -----------------------------------------------------

    retry_validation = validate_python_code(
        retry_code
    )

    if retry_validation.get("valid"):
        return retry_code

    # -----------------------------------------------------
    # FAILED
    # -----------------------------------------------------

    return ""


# =========================================================
# EXECUTE PYTHON WITH REPAIR
# =========================================================

def execute_script_with_repair(
    code,
    user_request,
):

    code = clean_python_code(code)

    if not code:

        return {
            "success": False,
            "error": (
                "Qwen generated an empty script."
            ),
        }

    current_code = code

    repair_attempts = 0

    while True:

        result = tool_execute_python(
            current_code
        )

        if result.get("success"):

            output = (
                result.get("output")
                or result.get("stdout")
                or result.get("result")
                or ""
            )

            output = str(
                output
            ).strip()

            return {
                "success": True,
                "output": output or "Done.",
                "path": result.get("path"),
            }

        error_text = str(
            result.get(
                "error",
                "Script failed.",
            )
        )

        if (
            repair_attempts
            >= MAX_SCRIPT_REPAIR_ATTEMPTS
        ):

            return {
                "success": False,
                "error": error_text,
                "path": result.get("path"),
            }

        repair_attempts += 1

        print(
            f"🔧 Repairing generated script "
            f"({repair_attempts}/"
            f"{MAX_SCRIPT_REPAIR_ATTEMPTS})..."
        )

        try:

            repaired = repair_script(
                current_code,
                error_text,
                user_request,
            )

        except Exception as e:

            return {
                "success": False,
                "error": (
                    f"Script failed and repair failed: {e}"
                ),
            }

        if not repaired:

            return {
                "success": False,
                "error": error_text,
            }

        current_code = repaired


# =========================================================
# HTML FILE HANDLING
# =========================================================

HTML_DIR = (
    PROJECT_DIR
    / "generated_files"
)

HTML_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def is_html_request(text):
    """
    Detect requests where the user wants an HTML file/page.
    """

    normalized = clean_text(text).lower()

    patterns = [
        r"\bhtml\b",
        r"\bhtml file\b",
        r"\bhtml page\b",
        r"\bwebsite\b",
        r"\blanding page\b",
        r"\bweb page\b",
        r"\bwebpage\b",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


def extract_html_code(response):
    """
    Extract HTML from Qwen's response.

    Supports:
        raw HTML
        ```html ... ```
        ``` ... ```
    """

    response = str(
        response or ""
    ).strip()

    # Remove markdown fences
    response = re.sub(
        r"^```html\s*",
        "",
        response,
        flags=re.IGNORECASE,
    )

    response = re.sub(
        r"^```\s*",
        "",
        response,
    )

    response = re.sub(
        r"\s*```$",
        "",
        response,
    )

    response = response.strip()

    # If Qwen added text before the HTML,
    # start from <!DOCTYPE or <html.
    doctype = re.search(
        r"<!DOCTYPE\s+html",
        response,
        re.IGNORECASE,
    )

    html_tag = re.search(
        r"<html\b",
        response,
        re.IGNORECASE,
    )

    if doctype:
        response = response[
            doctype.start():
        ]

    elif html_tag:
        response = response[
            html_tag.start():
        ]

    return response.strip()


def save_html_file(
    code,
):
    timestamp = int(
        time.time() * 1000
    )

    path = (
        HTML_DIR
        / f"jarvis_{timestamp}.html"
    )

    path.write_text(
        code,
        encoding="utf-8",
    )

    return path


def create_and_open_html(
    user_request,
):
    """
    Ask Qwen to generate HTML directly,
    save it as .html and open it in the
    user's default browser.

    The HTML is NOT executed as Python.
    """

    print(
        "🌐 Asking Qwen to generate HTML..."
    )

    messages = [
        {
            "role": "system",
            "content": """
You are Jarvis, a Windows AI assistant.

The user wants an HTML file.

Generate ONLY complete HTML source code.

IMPORTANT:
- Return HTML, NOT Python.
- Do not wrap the HTML in Markdown fences.
- Do not explain anything.
- Do not say "here is the HTML".
- Do not use Python.
- Do not use input().
- The result must be a complete standalone HTML document.
- CSS must be inside <style>.
- JavaScript, if needed, must be inside <script>.
- Make the page visually polished and functional.
- Use UTF-8.
- The file will be saved directly as an .html file and opened in a browser.

Return ONLY the HTML source.
""",
        },
        {
            "role": "user",
            "content": user_request,
        },
    ]

    try:
        response = ask_ollama(
            messages,
            temperature=0.2,
        )
    except Exception as e:
        return (
            f"I couldn't generate the HTML file: {e}"
        )

    code = extract_html_code(
        response
    )

    if not code:
        return (
            "Qwen did not generate any HTML."
        )

    # Basic validation
    if (
        "<html" not in code.lower()
        and "<!doctype html" not in code.lower()
    ):
        return (
            "Qwen generated invalid HTML."
        )

    try:
        path = save_html_file(
            code
        )
    except Exception as e:
        return (
            f"I couldn't save the HTML file: {e}"
        )

    print(
        f"📄 HTML file: {path}"
    )

    try:
        webbrowser.open(
            path.as_uri()
        )
    except Exception as e:
        return (
            f"I created the HTML file at {path}, "
            f"but couldn't open it automatically: {e}"
        )

    return (
        f"I created the HTML file and opened it in your browser"
    )

# =========================================================
# HANDLE QWEN
# =========================================================

def handle_with_qwen(text):

    try:

        action = ask_qwen_for_action(
            text
        )

    except Exception as e:

        return (
            f"I couldn't contact the AI model: {e}"
        )

    # -----------------------------------------------------
    # Make sure Qwen returned a dictionary
    # -----------------------------------------------------

    if not isinstance(
        action,
        dict,
    ):

        return (
            "Qwen returned an invalid response."
        )

    mode = str(
        action.get(
            "mode",
            "answer",
        )
    ).lower().strip()

    # =====================================================
    # ANSWER
    # =====================================================

    if mode == "answer":

        answer = clean_text(
            action.get(
                "answer",
                "",
            )
        )

        if answer:
            return answer

        return (
            "I don't have an answer for that."
        )

    # =====================================================
    # FILE
    # =====================================================

    if mode == "file":

        print(
            "📄 Jarvis is creating a file..."
        )

        return handle_file_action(
            action
        )

    # =====================================================
    # SCRIPT
    # =====================================================

    if mode == "script":

        reason = clean_text(
            action.get(
                "reason",
                "",
            )
        )

        code = clean_python_code(
            action.get(
                "code",
                "",
            )
        )

        if reason:

            print(
                f"💡 Reason: {reason}"
            )

        # -------------------------------------------------
        # Empty code
        # -------------------------------------------------

        if not code:

            return (
                "Qwen decided to use a script, "
                "but did not generate Python code."
            )

        # -------------------------------------------------
        # Validate BEFORE running
        #
        # This prevents errors such as:
        #
        # Final answer: The CPU speed is 2.4 GHz.
        #
        # from being executed as Python.
        # -------------------------------------------------

        validation = validate_python_code(
            code
        )

        if not validation.get(
            "valid"
        ):

            print(
                "⚠️ Qwen generated invalid Python."
            )

            validation_error = validation.get(
                "error",
                "Invalid Python code.",
            )

            print(
                "🔧 Asking Qwen to repair the Python..."
            )

            try:

                repaired = repair_script(
                    original_code=code,
                    error_text=validation_error,
                    user_request=text,
                )

            except Exception as e:

                return (
                    "Qwen generated invalid Python "
                    "and the repair failed: "
                    f"{e}"
                )

            if not repaired:

                return (
                    "Qwen generated invalid Python "
                    "and could not generate a valid "
                    "replacement script."
                )

            code = repaired

        # -------------------------------------------------
        # Final safety validation
        # -------------------------------------------------

        final_validation = validate_python_code(
            code
        )

        if not final_validation.get(
            "valid"
        ):

            return (
                "Qwen generated a Python script, "
                "but the code is still invalid."
            )

        # -------------------------------------------------
        # Execute
        # -------------------------------------------------

        print(
            "🐍 Jarvis generated a Python script."
        )

        result = execute_script_with_repair(
            code,
            text,
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if result.get(
            "success"
        ):

            output = str(
                result.get(
                    "output",
                    "Done.",
                )
            ).strip()

            if output:
                return output

            return "Done."

        # -------------------------------------------------
        # FAILURE
        # -------------------------------------------------

        error = str(
            result.get(
                "error",
                "Unknown script error.",
            )
        ).strip()

        return (
            "I tried to perform the operation, "
            "but the generated Python script failed:\n"
            f"{error}"
        )

    # =====================================================
    # UNKNOWN
    # =====================================================

    return (
        "I couldn't determine how to perform that request."
    )

# =========================================================
# MAIN AGENT
# =========================================================

def run_agent(text):

    text = clean_text(text)

    if not text:
        return ""

    # =====================================================
    # MEMORY
    # =====================================================
    # Handle explicit memory commands such as:
    # "remember my age is 13"
    # "remember my favorite game is Fortnite"
    #
    # If this is a memory command, handle it immediately
    # and do NOT send it through the rest of the agent.
    # =====================================================

    memory_result = handle_memory_command(
        text
    )

    if memory_result is not None:
        return memory_result

    # =====================================================
    # PENDING ACTION
    # =====================================================

    pending_result = handle_pending_action(
        text
    )

    if pending_result is not None:
        return pending_result

    # =====================================================
    # APPLICATION COMMANDS
    # =====================================================

    result = try_application_command(
        text
    )

    if result is not None:
        return result

    # =====================================================
    # SIMPLE COMMANDS
    # =====================================================

    result = handle_simple_commands(
        text
    )

    if result is not None:
        return result

    # =====================================================
    # HTML FILE REQUESTS
    # =====================================================

    if is_html_request(text):
        return create_and_open_html(
            text
        )

    # =====================================================
    # EVERYTHING ELSE → QWEN
    # =====================================================

    return handle_with_qwen(
        text
    )

# =========================================================
# TEST MODE
# =========================================================

if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "          JARVIS CORE TEST MODE"
    )

    print(
        "========================================"
    )

    print(
        f"Model: {MODEL}"
    )

    print()

    while True:

        try:

            text = input(
                "You: "
            ).strip()

        except KeyboardInterrupt:

            print()
            break

        except EOFError:

            break

        if not text:
            continue

        if text.lower() in {
            "exit",
            "quit",
        }:

            break

        try:

            answer = run_agent(
                text
            )

            print(
                f"Jarvis: {answer}"
            )

        except Exception as e:

            print(
                f"ERROR: {e}"
            )

        print()