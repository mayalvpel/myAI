import subprocess
import sys
import uuid
from pathlib import Path


# =========================================================
# DIRECTORIES
# =========================================================

PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

SCRIPT_DIR = (
    PROJECT_DIR
    / "scripts"
    / "generated"
)

SCRIPT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# CREATE SCRIPT
# =========================================================

def create_script(
    code: str,
    language: str = "python",
    name: str | None = None,
):

    if not code:

        return {
            "success": False,
            "error": "No code was provided."
        }

    language = str(
        language or "python"
    ).lower().strip()

    extensions = {

        "python": ".py",
        "py": ".py",

        "powershell": ".ps1",
        "powershell_script": ".ps1",
        "ps1": ".ps1",
        "ps": ".ps1",
    }

    extension = extensions.get(
        language
    )

    if not extension:

        return {
            "success": False,
            "error": (
                "Only Python and PowerShell "
                "scripts are supported."
            )
        }

    # -----------------------------------------------------
    # Safe filename
    # -----------------------------------------------------

    if not name:

        name = (
            "jarvis_"
            f"{uuid.uuid4().hex[:8]}"
        )

    safe_name = "".join(
        char
        for char in str(name)
        if char.isalnum()
        or char in "_-"
    )

    if not safe_name:

        safe_name = (
            "jarvis_"
            f"{uuid.uuid4().hex[:8]}"
        )

    path = (
        SCRIPT_DIR
        / f"{safe_name}{extension}"
    )

    try:

        path.write_text(
            str(code),
            encoding="utf-8"
        )

        return {
            "success": True,
            "path": str(path),
            "language": language,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# RUN PYTHON
# =========================================================

def run_python(
    path: Path,
    timeout: int = 120,
):

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "error": (
                f"Script exceeded "
                f"{timeout} seconds."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# RUN POWERSHELL
# =========================================================

def run_powershell(
    path: Path,
    timeout: int = 120,
):

    try:

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "error": (
                f"Script exceeded "
                f"{timeout} seconds."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# RUN SCRIPT
# =========================================================

def run_script(
    path: str,
    timeout: int = 120,
):

    if not path:

        return {
            "success": False,
            "error": "No script path."
        }

    try:

        script_path = Path(
            path
        ).resolve()

        generated_dir = (
            SCRIPT_DIR.resolve()
        )

        # -------------------------------------------------
        # Security:
        # only generated scripts.
        # -------------------------------------------------

        try:

            script_path.relative_to(
                generated_dir
            )

        except ValueError:

            return {
                "success": False,
                "error": (
                    "For security reasons, "
                    "Jarvis can only execute scripts "
                    "inside scripts/generated."
                ),
            }

        if not script_path.exists():

            return {
                "success": False,
                "error": "Script does not exist."
            }

        if not script_path.is_file():

            return {
                "success": False,
                "error": "Script path is not a file."
            }

        # -------------------------------------------------
        # Python
        # -------------------------------------------------

        if script_path.suffix.lower() == ".py":

            return run_python(
                script_path,
                timeout
            )

        # -------------------------------------------------
        # PowerShell
        # -------------------------------------------------

        if script_path.suffix.lower() == ".ps1":

            return run_powershell(
                script_path,
                timeout
            )

        return {
            "success": False,
            "error": (
                "Unsupported script type."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }