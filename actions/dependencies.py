import re
import sys
import subprocess
import importlib.util


def install_python_package(package: str) -> str:
    """Install a Python package using the same Python running Jarvis."""

    package = str(package).strip()

    if not package:
        return "ERROR: No package specified."

    # Basic safety: only allow normal PyPI package names.
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", package):
        return f"ERROR: Invalid package name: {package}"

    print(f"📦 Installing Python package: {package}")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                package,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            return (
                f"ERROR: Failed to install {package}\n"
                f"{result.stderr[-2000:]}"
            )

        return f"PACKAGE_INSTALLED: {package}"

    except subprocess.TimeoutExpired:
        return f"ERROR: Package installation timed out: {package}"

    except Exception as e:
        return f"ERROR: Package installation failed: {e}"


def package_available(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except Exception:
        return False