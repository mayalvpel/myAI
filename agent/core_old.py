import ast
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from pymsgbox import prompt
import requests


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = "qwen3:1.7b"

OLLAMA_URL = "http://localhost:11434/api/generate"

PROJECT_DIR = Path.cwd().resolve()

SCRIPT_DIR = PROJECT_DIR / "agent" / "generated_scripts"

SCRIPT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SCRIPT_TIMEOUT = 120
MAX_REPAIR_ATTEMPTS = 3


# =========================================================
# JARVIS SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = r"""
You are Jarvis, a Windows desktop AI assistant.

Your job is to actually perform the user's request.

You have access to the user's Windows computer through Python
scripts that you can generate and execute.

=========================================================
GENERAL RULE
=========================================================

Do NOT guess information about the computer.

If the answer depends on the computer, Windows, filesystem,
network, installed applications, disk space, CPU, RAM,
processes, environment variables, IP addresses, hardware,
system configuration, files, folders, or any other live
computer state, generate Python code to obtain the real value.

The Python script will be executed on the user's computer.

The script MUST print the final answer.

=========================================================
WHEN TO ANSWER DIRECTLY
=========================================================

If you already know the answer and it does not require
access to the user's computer, return a direct answer.

Example:

User:
What is 2 + 2?

Return:

{
    "action": "answer",
    "answer": "4"
}

=========================================================
WHEN TO GENERATE PYTHON
=========================================================

If the request requires performing an operation on the user's
computer or obtaining live information from it, generate
Python.

Examples:

- What is my internal IP?
- What is my public IP?
- How much space is left on C drive?
- What CPU do I have?
- How much RAM do I have?
- What files are in Downloads?
- Is Telegram installed?
- What processes are running?
- What is my Windows username?
- What is the computer name?
- Create a folder.
- Rename a file.
- Find a file.
- Delete a file if explicitly requested.
- Check network connectivity.
- Get Wi-Fi information.
- Perform an operation for which no dedicated tool exists.

=========================================================
PYTHON REQUIREMENTS
=========================================================

The generated Python must:

1. Be complete.
2. Be valid Python.
3. Actually perform the requested operation.
4. Print the final result.
5. Never merely explain how to do the operation.
6. Work on Windows.
7. Use standard-library modules whenever possible.

=========================================================
WINDOWS PATHS
=========================================================

IMPORTANT:

NEVER generate:

    'C:\'

This is invalid Python because the final backslash escapes
the quote.

Instead use:

    "C:/"

or:

    "C:\\"

or:

    r"C:\"

Prefer:

    Path("C:/")

For example:

    import shutil

    total, used, free = shutil.disk_usage("C:/")

    print(
        f"{free / (1024 ** 3):.2f} GB free"
    )

=========================================================
IP ADDRESSES
=========================================================

If the user asks for the INTERNAL / LOCAL IP:

Use the computer's network configuration.

For example:

    import socket

    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    print(ip)

Do NOT return the public IP when the user asks for
the internal/local IP.

If the user asks for the PUBLIC IP:

Use the internet, for example:

    import urllib.request

    ip = urllib.request.urlopen(
        "https://api.ipify.org",
        timeout=10
    ).read().decode().strip()

    print(ip)

Do not confuse public IP and internal IP.

=========================================================
DISK SPACE
=========================================================

For disk space use:

    import shutil

    total, used, free = shutil.disk_usage("C:/")

    print(
        f"{free / (1024 ** 3):.2f} GB free"
    )

=========================================================
PACKAGES
=========================================================

Prefer the Python standard library.

If an external package is genuinely required, the generated
script may install it automatically.

Example:

    import subprocess
    import sys

    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "PACKAGE_NAME"
    ])

Then import the package.

Do not install packages unnecessarily.

=========================================================
WINDOWS COMMANDS
=========================================================

You may use subprocess for Windows operations.

Do not use deprecated commands if a modern Python or PowerShell
alternative exists.

For example, do NOT rely on WMIC for disk information.

Use Python's shutil.disk_usage instead.

=========================================================
APPLICATIONS
=========================================================

If the user asks to open, close, or interact with an application
and a dedicated application mechanism is available, use it.

If there is no dedicated mechanism available, you may generate
Python/PowerShell to perform the requested operation.

Do not claim that an application was opened unless the operation
actually succeeded.

=========================================================
OUTPUT FORMAT
=========================================================

You MUST return ONLY JSON.

If you can answer directly:

{
    "action": "answer",
    "answer": "your answer"
}

If Python is required:

{
    "action": "script",
    "reason": "short explanation",
    "code": "complete Python code"
}

The "code" value must contain raw Python code as a JSON string.

Do NOT use Markdown fences.

Do NOT output:

```python
...
Do NOT output commentary outside JSON.

=========================================================
IMPORTANT

Do not guess.

Do not hallucinate computer information.

If the computer must be queried, generate and execute Python.
"""

def ask_qwen(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,

        # Disable Qwen thinking.
        "think": False,

        "stream": False,

        "options": {
            "temperature": 0.1,
            "num_predict": 1500,
        },
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    data = response.json()

    return str(
        data.get(
            "response",
            ""
        )
    ).strip()


# =========================================================
# JSON PARSER
# =========================================================

def extract_json(text: str):

    if not text:
        return None

    text = str(text).strip()

    # Remove markdown fences if the model ignored instructions.
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # First attempt.
    try:

        return json.loads(
            text
        )

    except Exception:
        pass

    # Search for JSON object inside response.
    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except Exception:
            pass

    return None

# =========================================================
# PYTHON VALIDATION
# =========================================================
def validate_python(code: str):
    if not code:

        return (
            False,
            "Generated script is empty."
        )

    try:

        ast.parse(
            code
        )

        return (
            True,
            ""
        )

    except SyntaxError as e:

        return (
            False,
            (
                f"SyntaxError: {e.msg} "
                f"(line {e.lineno}, "
                f"column {e.offset})"
            )
        )

    except Exception as e:

        return (
            False,
            str(e)
        )

# =========================================================
# COMMON WINDOWS PATH REPAIR
# =========================================================
def repair_common_windows_paths(
    code: str
    ) -> str:

    if not code:
        return code

    # Common broken paths produced by small models.
    code = code.replace(
        "'C:\\'",
        "'C:/'"
    )

    code = code.replace(
        '"C:\\"',
        '"C:/"'
    )

    return code

# =========================================================
# SAVE SCRIPT
# =========================================================
def save_script(
    code: str
    ) -> Path:

    timestamp = int(
        time.time() * 1000
    )

    script_path = (
        SCRIPT_DIR
        / f"jarvis_{timestamp}.py"
    )

    script_path.write_text(
        code,
        encoding="utf-8"
    )

    return script_path

# =========================================================
# RUN SCRIPT
# =========================================================
def run_script(
    script_path: Path
    ):

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],

            capture_output=True,

            text=True,

            encoding="utf-8",

            errors="replace",

            timeout=SCRIPT_TIMEOUT,
        )

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "stdout": "",
            "stderr": (
                "The generated script timed out."
            ),
            "returncode": None,
        }

    except Exception as e:

        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": None,
        }

    stdout = (
        result.stdout
        or ""
    ).strip()

    stderr = (
        result.stderr
        or ""
    ).strip()

    return {
        "success": (
            result.returncode == 0
        ),
        "stdout": stdout,
        "stderr": stderr,
        "returncode": result.returncode,
    }

# =========================================================
# REPAIR SCRIPT USING QWEN
# =========================================================
def repair_script(
    original_code: str,
    error: str,
    ):

    repair_prompt = f"""

    The Python script you generated failed on the user's Windows
    computer.

    You MUST repair it.

    =========================================================
    ERROR

    {error}

    =========================================================
    ORIGINAL SCRIPT

    {original_code}

    =========================================================
    REQUIREMENTS

    Return ONLY JSON.

    Use exactly:

    {{
    "action": "script",
    "reason": "short explanation",
    "code": "complete corrected Python code"
    }}

    The corrected code MUST:

    be valid Python
    work on Windows
    actually perform the original task
    print the final result
    not merely explain the solution
    not use invalid Windows strings such as 'C:\'
    preferably use pathlib
    preferably use forward-slash paths
    use the standard library where possible

    Do not use Markdown code fences.

    Do not put anything outside the JSON object.
    """

    try:

        raw = ask_qwen(
            repair_prompt
        )

        parsed = extract_json(
            raw
        )

        if not parsed:
            return None

        if (
            parsed.get("action")
            != "script"
        ):
            return None

        code = parsed.get(
            "code",
            ""
        )

        if not code:
            return None

        return str(
            code
        ).strip()

    except Exception as e:

        print(
            f"❌ Script repair error: {e}"
        )

        return None

# =========================================================
# EXECUTE GENERATED SCRIPT
# =========================================================
def execute_generated_script(
    code: str,
    reason: str,
    ):

    code = repair_common_windows_paths(
        code
    )

    for attempt in range(
        MAX_REPAIR_ATTEMPTS + 1
    ):

        # -------------------------------------------------
        # Validate syntax
        # -------------------------------------------------

        valid, error = (
            validate_python(
                code
            )
        )

        if not valid:

            print(
                "⚠️ Generated Python "
                "has invalid syntax."
            )

            if (
                attempt
                >= MAX_REPAIR_ATTEMPTS
            ):

                return (
                    "I generated Python code, "
                    "but it was invalid and "
                    "could not be repaired."
                )

            repaired = repair_script(
                code,
                error,
            )

            if not repaired:

                return (
                    "I generated Python code, "
                    "but I could not repair it."
                )

            code = (
                repair_common_windows_paths(
                    repaired
                )
            )

            continue

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        script_path = save_script(
            code
        )

        print(
            "🐍 Jarvis generated a script."
        )

        if reason:

            print(
                f"💡 Reason: {reason}"
            )

        print(
            f"📄 Script: {script_path}"
        )

        print(
            "▶️ Running script..."
        )

        # -------------------------------------------------
        # Run
        # -------------------------------------------------

        result = run_script(
            script_path
        )

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if result["success"]:

            output = (
                result.get(
                    "stdout",
                    ""
                )
                or
                result.get(
                    "stderr",
                    ""
                )
            ).strip()

            if output:
                return output

            return (
                "The operation completed successfully, "
                "but the script did not return a result."
            )

        # -------------------------------------------------
        # FAILURE
        # -------------------------------------------------

        error = (
            result.get(
                "stderr",
                ""
            )
            or
            result.get(
                "stdout",
                ""
            )
            or
            "Unknown script error."
        )

        print(
            "⚠️ Script failed."
        )

        if (
            attempt
            >= MAX_REPAIR_ATTEMPTS
        ):

            return (
                "I tried to perform the operation, "
                "but the generated script failed:\n"
                f"{error}"
            )

        print(
            f"🔧 Asking Qwen to repair the "
            f"script ({attempt + 1}/"
            f"{MAX_REPAIR_ATTEMPTS})..."
        )

        repaired = repair_script(
            code,
            error,
        )

        if not repaired:

            return (
                "I tried to perform the operation, "
                "but the generated script failed:\n"
                f"{error}"
            )

        code = (
            repair_common_windows_paths(
                repaired
            )
        )

    return (
        "I couldn't successfully execute "
        "the operation."
    )

# =========================================================
# DIRECT ANSWER
# =========================================================
def handle_answer(
    response
    ):

    answer = response.get(
        "answer",
        ""
    )

    if answer is None:
        return ""

    return str(
        answer
    ).strip()
# =========================================================
# MAIN AGENT
# =========================================================

def run_agent(
    text: str
    ) -> str:

    text = str(
        text or ""
    ).strip()

    if not text:
        return ""

    print(
        "🧠 Asking Qwen..."
    )

    # =====================================================
    # ASK QWEN
    # =====================================================

    try:

        raw = ask_qwen(
            text
        )

    except requests.exceptions.ConnectionError:

        return (
            "I can't connect to Ollama. "
            "Please make sure Ollama is running."
        )

    except requests.exceptions.Timeout:

        return (
            "Ollama took too long to respond."
        )

    except Exception as e:

        return (
            f"Qwen error: {e}"
        )

    # =====================================================
    # PARSE
    # =====================================================

    response = extract_json(
        raw
    )

    # =====================================================
    # MODEL DID NOT RETURN JSON
    # =====================================================

    if response is None:

        return raw

    if not isinstance(
        response,
        dict
    ):

        return raw

    action = str(
        response.get(
            "action",
            ""
        )
    ).lower().strip()

    # =====================================================
    # DIRECT ANSWER
    # =====================================================

    if action == "answer":

        return handle_answer(
            response
        )

    # =====================================================
    # SCRIPT
    # =====================================================

    if action == "script":

        code = str(
            response.get(
                "code",
                ""
            )
        ).strip()

        reason = str(
            response.get(
                "reason",
                ""
            )
        ).strip()

        if not code:

            return (
                "Qwen decided that a script "
                "was required, but it did not "
                "generate any Python code."
            )

        return execute_generated_script(
            code,
            reason,
        )

    # =====================================================
    # UNKNOWN ACTION
    # =====================================================

    return raw
# =========================================================
# TEST MODE
# =========================================================
if __name__ == "__main__":

    print(
        "========================================"
    )

    print(
        "       JARVIS CORE TEST MODE"
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

            print(
                "\nGoodbye."
            )

            break

        if not text:
            continue

        if text.lower() in {
            "exit",
            "quit",
            "goodbye",
        }:

            print(
                "Goodbye."
            )

            break

        try:

            answer = run_agent(
                text
            )

            print()

            print(
                f"Jarvis: {answer}"
            )

            print()

        except Exception as e:

            print()

            print(
                f"❌ Agent error: {e}"
            )

            print()