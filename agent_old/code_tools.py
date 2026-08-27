from pathlib import Path
import subprocess
import sys


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = Path(
    r"C:\myAI"
).resolve()


# =========================================================
# PATH SAFETY
# =========================================================

def resolve_project_path(path: str) -> Path:
    """
    Resolve a path inside the JARVIS project.

    JARVIS is not allowed to access files outside
    the project directory through these tools.
    """

    if not path or not str(path).strip():
        raise ValueError(
            "A file path is required."
        )

    path = str(path).strip()

    target = (
        PROJECT_ROOT / path
    ).resolve()

    try:

        target.relative_to(
            PROJECT_ROOT
        )

    except ValueError:

        raise ValueError(
            "Access outside the project directory is not allowed."
        )

    return target


# =========================================================
# CREATE FILE
# =========================================================

def create_file(
    path: str,
    content: str
) -> str:
    """
    Create a new file inside the project.

    Does not overwrite an existing file.
    """

    try:

        file_path = resolve_project_path(
            path
        )

        if file_path.exists():

            return (
                f"ERROR: File already exists: {path}"
            )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Created file: {path}"
        )

    except Exception as e:

        return (
            f"ERROR: Could not create file: {e}"
        )


# =========================================================
# READ FILE
# =========================================================

def read_file(
    path: str
) -> str:
    """
    Read a text file inside the project.
    """

    try:

        file_path = resolve_project_path(
            path
        )

        if not file_path.exists():

            return (
                f"ERROR: File does not exist: {path}"
            )

        if not file_path.is_file():

            return (
                f"ERROR: Path is not a file: {path}"
            )

        content = file_path.read_text(
            encoding="utf-8"
        )

        return content

    except UnicodeDecodeError:

        return (
            f"ERROR: File is not a UTF-8 text file: {path}"
        )

    except Exception as e:

        return (
            f"ERROR: Could not read file: {e}"
        )


# =========================================================
# WRITE / REPLACE FILE
# =========================================================

def write_file(
    path: str,
    content: str
) -> str:
    """
    Write or replace a file inside the project.
    """

    try:

        file_path = resolve_project_path(
            path
        )

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Updated file: {path}"
        )

    except Exception as e:

        return (
            f"ERROR: Could not write file: {e}"
        )


# =========================================================
# OPEN IN VS CODE
# =========================================================

def open_in_vscode(
    path: str = "."
) -> str:
    """
    Open a project file or directory in VS Code.
    """

    try:

        target = resolve_project_path(
            path
        )

        if not target.exists():

            return (
                f"ERROR: Path does not exist: {path}"
            )

        subprocess.Popen(
            [
                "code",
                str(target)
            ],
            shell=True
        )

        return (
            f"Opened {path} in VS Code."
        )

    except Exception as e:

        return (
            f"ERROR: Could not open VS Code: {e}"
        )


# =========================================================
# RUN PYTHON FILE
# =========================================================

# =========================================================
# RUN PYTHON FILE
# =========================================================

def run_python(
    path: str
) -> str:
    """
    Run a Python file inside the project.

    Automatically detects ModuleNotFoundError,
    installs the missing package with pip,
    and retries the script.

    Captures stdout and stderr.
    """

    MAX_ATTEMPTS = 5

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

    def extract_missing_module(error_text):
        """
        Extract:

        ModuleNotFoundError:
        No module named 'psutil'

        Returns:

        psutil
        """

        import re

        patterns = [
            r"No module named ['\"]([^'\"]+)['\"]",
            r"No module named ([A-Za-z0-9_.-]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                error_text,
                re.IGNORECASE,
            )

            if match:
                module = (
                    match.group(1)
                    .split(".")[0]
                    .strip()
                )

                if module:
                    return module

        return None

    def install_package(package_name):

        print(
            f"📦 Installing missing Python package: "
            f"{package_name}"
        )

        # -------------------------------------------------
        # Make sure pip exists.
        # -------------------------------------------------

        pip_check = subprocess.run(
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

        if pip_check.returncode != 0:

            print(
                "📦 pip is unavailable. "
                "Bootstrapping pip..."
            )

            ensurepip_result = subprocess.run(
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

            if ensurepip_result.returncode != 0:

                print(
                    "❌ Could not install pip."
                )

                if ensurepip_result.stderr:
                    print(
                        ensurepip_result.stderr
                    )

                return False

        # -------------------------------------------------
        # Install package.
        # -------------------------------------------------

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "--upgrade",
                package_name,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:

            print(
                f"✅ Successfully installed "
                f"{package_name}"
            )

            return True

        print(
            f"❌ Failed to install "
            f"{package_name}"
        )

        if result.stderr:
            print(
                result.stderr
            )

        return False

    # =====================================================
    # VALIDATE PATH
    # =====================================================

    try:

        file_path = resolve_project_path(
            path
        )

    except Exception as e:

        return (
            f"ERROR: Invalid Python path: {e}"
        )

    if not file_path.exists():

        return (
            f"ERROR: Python file does not exist: {path}"
        )

    if not file_path.is_file():

        return (
            f"ERROR: Path is not a file: {path}"
        )

    if file_path.suffix.lower() != ".py":

        return (
            "ERROR: run_python only accepts .py files."
        )

    # =====================================================
    # EXECUTION / AUTO-INSTALL LOOP
    # =====================================================

    attempted_packages = set()

    for attempt in range(MAX_ATTEMPTS):

        print(
            f"▶️ Running Python: {path} "
            f"(attempt {attempt + 1}/{MAX_ATTEMPTS})"
        )

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    str(file_path),
                ],
                cwd=str(
                    PROJECT_ROOT
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

        except subprocess.TimeoutExpired:

            return (
                "ERROR: Python execution "
                "timed out after 30 seconds."
            )

        except Exception as e:

            return (
                f"ERROR: Could not run Python file: {e}"
            )

        output = (
            result.stdout.strip()
        )

        errors = (
            result.stderr.strip()
        )

        # =================================================
        # SUCCESS
        # =================================================

        if result.returncode == 0:

            parts = [
                "Exit code: 0"
            ]

            if output:

                parts.append(
                    "STDOUT:\n"
                    + output
                )

            parts.append(
                "STATUS: SUCCESS"
            )

            return "\n\n".join(
                parts
            )

        # =================================================
        # CHECK FOR MISSING MODULE
        # =================================================

        missing_module = (
            extract_missing_module(
                errors
            )
        )

        if missing_module:

            package_name = (
                IMPORT_TO_PIP.get(
                    missing_module,
                    missing_module,
                )
            )

            # Prevent infinite attempts if the same
            # package keeps failing.

            if package_name in attempted_packages:

                return (
                    f"Exit code: {result.returncode}\n\n"
                    f"STDOUT:\n{output}\n\n"
                    f"STDERR:\n{errors}\n\n"
                    "STATUS: FAILED\n\n"
                    f"Package '{package_name}' "
                    "was already installed/attempted "
                    "but the module is still unavailable."
                )

            attempted_packages.add(
                package_name
            )

            print(
                f"🔎 Missing Python module detected: "
                f"{missing_module}"
            )

            print(
                f"📦 Required pip package: "
                f"{package_name}"
            )

            installed = install_package(
                package_name
            )

            if installed:

                print(
                    "🔄 Package installed. "
                    "Retrying Python script..."
                )

                continue

            return (
                f"Exit code: {result.returncode}\n\n"
                f"STDOUT:\n{output}\n\n"
                f"STDERR:\n{errors}\n\n"
                "STATUS: FAILED\n\n"
                f"Could not install required "
                f"package: {package_name}"
            )

        # =================================================
        # OTHER ERROR
        # =================================================

        parts = [
            f"Exit code: {result.returncode}"
        ]

        if output:

            parts.append(
                "STDOUT:\n"
                + output
            )

        if errors:

            parts.append(
                "STDERR:\n"
                + errors
            )

        parts.append(
            "STATUS: FAILED"
        )

        return "\n\n".join(
            parts
        )

    return (
        "ERROR: Python execution failed after "
        f"{MAX_ATTEMPTS} attempts."
    )

# =========================================================
# LIST PROJECT FILES
# =========================================================

def list_files(
    path: str = "."
) -> str:
    """
    List files and directories inside the project.
    """

    try:

        directory = resolve_project_path(
            path
        )

        if not directory.exists():

            return (
                f"ERROR: Directory does not exist: {path}"
            )

        if not directory.is_dir():

            return (
                f"ERROR: Path is not a directory: {path}"
            )

        entries = []

        for item in sorted(
            directory.iterdir(),
            key=lambda x: (
                not x.is_dir(),
                x.name.lower()
            )
        ):

            if item.name in {
                ".git",
                ".venv",
                "__pycache__"
            }:

                continue

            if item.is_dir():

                entries.append(
                    f"[DIR]  {item.name}"
                )

            else:

                entries.append(
                    f"[FILE] {item.name}"
                )

        if not entries:

            return "Directory is empty."

        return "\n".join(
            entries
        )

    except Exception as e:

        return (
            f"ERROR: Could not list files: {e}"
        )