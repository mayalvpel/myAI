import re
import subprocess
import time
from pathlib import Path

from agent.package_manager import (
    ensure_virtual_environment,
    install_missing_dependencies,
)


# =========================================================
# SETTINGS
# =========================================================

SCRIPT_TIMEOUT = 120
MAX_OUTPUT_LENGTH = 12000

PROJECT_DIR = Path(__file__).resolve().parent.parent

SCRIPT_DIRECTORY = (
    PROJECT_DIR / "generated_scripts"
)

MAX_DEPENDENCY_ATTEMPTS = 5
MAX_REPAIR_ATTEMPTS = 3


# =========================================================
# DIRECTORY
# =========================================================

def ensure_script_directory():
    SCRIPT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return SCRIPT_DIRECTORY


# =========================================================
# CLEAN PYTHON CODE
# =========================================================

def clean_python_code(code):
    """
    Clean common unwanted output from Qwen.

    Qwen may occasionally return:

        ```python
        print("hello")
        ```

    or:

        Here is the code:
        print("hello")

    or even:

        Final answer: The CPU speed is 2.4 GHz.

    This function tries to extract actual Python code.
    """

    code = str(code or "").strip()

    if not code:
        return ""

    # -----------------------------------------------------
    # Remove markdown fences
    # -----------------------------------------------------

    code = re.sub(
        r"^\s*```python\s*",
        "",
        code,
        flags=re.IGNORECASE,
    )

    code = re.sub(
        r"^\s*```\s*",
        "",
        code,
    )

    code = re.sub(
        r"\s*```\s*$",
        "",
        code,
    )

    code = code.strip()

    # -----------------------------------------------------
    # Remove common introductory phrases
    # -----------------------------------------------------

    prefixes = [
        "Here is the Python code:",
        "Here is the code:",
        "Python code:",
        "Generated Python code:",
        "Corrected Python code:",
        "Final answer:",
    ]

    for prefix in prefixes:
        if code.lower().startswith(prefix.lower()):
            code = code[len(prefix):].strip()

    # -----------------------------------------------------
    # If Qwen returned a fenced block somewhere inside text
    # -----------------------------------------------------

    match = re.search(
        r"```python\s*(.*?)```",
        code,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match:
        code = match.group(1).strip()

    else:

        match = re.search(
            r"```\s*(.*?)```",
            code,
            flags=re.DOTALL,
        )

        if match:
            code = match.group(1).strip()

    return code.strip()


# =========================================================
# VALIDATE PYTHON
# =========================================================

def validate_python_code(code):
    """
    Validate generated Python before executing it.

    Returns:

        {
            "valid": True
        }

    or:

        {
            "valid": False,
            "error": "..."
        }
    """

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
            "error": (
                f"SyntaxError: {e}"
            ),
        }

    except Exception as e:

        return {
            "valid": False,
            "error": str(e),
        }


# =========================================================
# SAVE SCRIPT
# =========================================================

def save_script(code):

    ensure_script_directory()

    timestamp = int(
        time.time() * 1000
    )

    path = (
        SCRIPT_DIRECTORY
        / f"jarvis_{timestamp}.py"
    )

    path.write_text(
        str(code),
        encoding="utf-8",
    )

    return path


# =========================================================
# RUN SCRIPT
# =========================================================

def run_script(script_path):
    script_path = Path(script_path).resolve()

    if not script_path.exists():
        return {
            "success": False,
            "error": f"Script does not exist: {script_path}",
        }

    env_result = ensure_virtual_environment()

    if not env_result.get("success"):
        return {
            "success": False,
            "error": (
                "Could not prepare Jarvis Python environment: "
                f"{env_result.get('error', '')}"
            ),
        }

    python_executable = env_result.get("python")

    if not python_executable:
        return {
            "success": False,
            "error": "Jarvis Python executable was not found.",
        }

    result_data = {}

    try:

        result = subprocess.run(
            [
                str(python_executable),
                str(script_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SCRIPT_TIMEOUT,
            cwd=str(script_path.parent),
        )

        stdout = (
            result.stdout or ""
        ).strip()

        stderr = (
            result.stderr or ""
        ).strip()

        if len(stdout) > MAX_OUTPUT_LENGTH:
            stdout = stdout[-MAX_OUTPUT_LENGTH:]

        if len(stderr) > MAX_OUTPUT_LENGTH:
            stderr = stderr[-MAX_OUTPUT_LENGTH:]

        if result.returncode == 0:

            result_data = {
                "success": True,
                "output": stdout,
                "stderr": stderr,
                "returncode": 0,
            }

        else:

            result_data = {
                "success": False,
                "output": stdout,
                "error": (
                    stderr
                    or stdout
                    or (
                        f"Python exited with code "
                        f"{result.returncode}"
                    )
                ),
                "returncode": result.returncode,
            }

    except subprocess.TimeoutExpired as e:

        stdout = e.stdout or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(
                "utf-8",
                errors="replace",
            )

        result_data = {
            "success": False,
            "error": "The Python script timed out.",
            "output": str(stdout)[-MAX_OUTPUT_LENGTH:],
        }

    except Exception as e:

        result_data = {
            "success": False,
            "error": str(e),
        }

    finally:

        # =====================================================
        # DELETE GENERATED PYTHON SCRIPT
        # =====================================================

        try:

            if script_path.exists():

                script_path.unlink()

                print(
                    f"🗑️ Deleted generated script: "
                    f"{script_path.name}"
                )

        except Exception as e:

            print(
                f"⚠️ Could not delete generated script: {e}"
            )

    return result_data

# =========================================================
# DEPENDENCY INSTALLATION
# =========================================================

def prepare_dependencies(code):

    """
    Ask package_manager to inspect the generated code
    and install missing Python packages.

    IMPORTANT:

    script_engine does NOT run pip directly.

    package_manager is responsible for:

        import -> package mapping
        virtual environment
        pip installation
    """

    result = install_missing_dependencies(
        code
    )

    if not isinstance(
        result,
        dict,
    ):

        return {
            "success": False,
            "error": (
                "package_manager returned "
                "an invalid result."
            ),
        }

    return result


# =========================================================
# GENERATE + RUN
# =========================================================

def run_generated_python(
    code,
    packages=None,
    max_attempts=3,
):
    """
    Main Python execution entry point.

    Flow:

        generated Python
              ↓
        dependency detection
              ↓
        package_manager
              ↓
        save script
              ↓
        validate Python
              ↓
        execute
    """

    code = clean_python_code(
        code
    )

    if not code:

        return {
            "success": False,
            "error": (
                "Generated Python code is empty."
            ),
        }

    # -----------------------------------------------------
    # Explicit packages
    #
    # packages are optional.
    #
    # The preferred mechanism is automatic dependency
    # detection through package_manager.
    # -----------------------------------------------------

    if packages:

        # We don't install them ourselves.
        # package_manager receives imports from code.
        pass

    # -----------------------------------------------------
    # Dependency detection
    # -----------------------------------------------------

    dependency_result = (
        prepare_dependencies(
            code
        )
    )

    if not dependency_result.get(
        "success"
    ):

        return {
            "success": False,
            "error": (
                "Could not prepare Python "
                "dependencies: "
                f"{dependency_result.get('error', '')}"
            ),
            "dependency_result": dependency_result,
        }

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    try:

        path = save_script(
            code
        )

    except Exception as e:

        return {
            "success": False,
            "error": (
                f"Could not save generated script: {e}"
            ),
        }

    print(
        "📄 Script:",
        path,
    )

    # -----------------------------------------------------
    # Validate before execution
    # -----------------------------------------------------

    validation = validate_python_code(
        code
    )

    if not validation.get(
        "valid"
    ):

        return {
            "success": False,
            "error": validation.get(
                "error",
                "Invalid Python code.",
            ),
            "path": str(
                path
            ),
        }

    # -----------------------------------------------------
    # Run
    # -----------------------------------------------------

    print(
        "▶️ Running script..."
    )

    return run_script(
        path
    )


# =========================================================
# SIMPLE EXECUTION HELPER
# =========================================================

def execute_python(
    code,
    packages=None,
):
    """
    Public helper used by core.py.

    Python code in -> dependency preparation
    -> execution -> result.
    """

    return run_generated_python(
        code=code,
        packages=packages,
    )


# =========================================================
# COMPATIBILITY ALIASES
# =========================================================

def execute_script(
    code,
    packages=None,
):
    """
    Compatibility alias.
    """

    return execute_python(
        code,
        packages=packages,
    )


def run_python(
    code,
    packages=None,
):
    """
    Compatibility alias.
    """

    return execute_python(
        code,
        packages=packages,
    )