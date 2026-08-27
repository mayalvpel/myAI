import ast
import importlib.util
import subprocess
import sys
from pathlib import Path


# =========================================================
# DIRECTORIES
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

SCRIPT_ENV = PROJECT_DIR / ".jarvis_venv"


# =========================================================
# PYTHON EXECUTABLE
# =========================================================

def get_python_executable():
    if sys.platform == "win32":
        return SCRIPT_ENV / "Scripts" / "python.exe"

    return SCRIPT_ENV / "bin" / "python"


# =========================================================
# CREATE VENV
# =========================================================

def ensure_virtual_environment():
    python = get_python_executable()

    if python.exists():
        return {
            "success": True,
            "python": str(python),
        }

    try:
        SCRIPT_ENV.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "venv",
                str(SCRIPT_ENV),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": (
                    result.stderr
                    or result.stdout
                    or "Failed to create virtual environment."
                ),
            }

        return {
            "success": True,
            "python": str(python),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# IMPORT → PIP PACKAGE MAP
# =========================================================

PACKAGE_MAP = {
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "wmi": "WMI",
}


# =========================================================
# STANDARD LIBRARY
# =========================================================

STDLIB_MODULES = {
    "os",
    "sys",
    "json",
    "re",
    "math",
    "time",
    "datetime",
    "pathlib",
    "subprocess",
    "socket",
    "urllib",
    "http",
    "csv",
    "sqlite3",
    "shutil",
    "glob",
    "random",
    "statistics",
    "typing",
    "collections",
    "itertools",
    "functools",
    "threading",
    "asyncio",
    "hashlib",
    "base64",
    "secrets",
    "tempfile",
    "platform",
    "logging",
    "traceback",
    "textwrap",
    "inspect",
    "argparse",
    "configparser",
    "xml",
    "email",
    "html",
    "zipfile",
    "tarfile",
    "gzip",
    "pickle",
    "struct",
    "enum",
    "dataclasses",
    "decimal",
    "fractions",
    "queue",
    "signal",
    "timeit",
    "unittest",
}


# =========================================================
# EXTRACT IMPORTS
# =========================================================

def extract_imports(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    modules = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:
                modules.add(
                    alias.name.split(".")[0]
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                modules.add(
                    node.module.split(".")[0]
                )

    return sorted(modules)


# =========================================================
# IS IMPORT AVAILABLE
# =========================================================

def import_available(
    module_name: str,
    python_executable=None,
):
    if module_name in STDLIB_MODULES:
        return True

    if python_executable:

        code = (
            "import importlib.util; "
            f"print(importlib.util.find_spec("
            f"'{module_name}') is not None)"
        )

        try:
            result = subprocess.run(
                [
                    str(python_executable),
                    "-c",
                    code,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )

            if (
                result.returncode == 0
                and result.stdout.strip() == "True"
            ):
                return True

        except Exception:
            pass

    return False


# =========================================================
# PACKAGE NAME
# =========================================================

def package_for_module(module: str):
    return PACKAGE_MAP.get(
        module,
        module,
    )


# =========================================================
# INSTALL PACKAGE
# =========================================================

def install_package(package: str):
    env = ensure_virtual_environment()

    if not env.get("success"):
        return env

    python = env["python"]

    print(
        f"📦 Installing dependency: {package}"
    )

    try:
        result = subprocess.run(
            [
                python,
                "-m",
                "pip",
                "install",
                package,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "package": package,
                "error": (
                    result.stderr
                    or result.stdout
                    or "pip installation failed."
                ),
            }

        return {
            "success": True,
            "package": package,
        }

    except Exception as e:
        return {
            "success": False,
            "package": package,
            "error": str(e),
        }


# =========================================================
# INSTALL MISSING DEPENDENCIES
# =========================================================

def install_missing_dependencies(code: str):
    env = ensure_virtual_environment()

    if not env.get("success"):
        return env

    python = env["python"]

    imports = extract_imports(code)

    installed = []
    failed = []

    for module in imports:

        if import_available(
            module,
            python,
        ):
            continue

        package = package_for_module(
            module
        )

        result = install_package(
            package
        )

        if result.get("success"):
            installed.append(package)
        else:
            failed.append({
                "module": module,
                "package": package,
                "error": result.get(
                    "error",
                    "",
                ),
            })

    return {
        "success": len(failed) == 0,
        "installed": installed,
        "failed": failed,
        "python": python,
    }