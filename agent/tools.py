from agent.app_manager import (
    normalize_app_name,
    find_application,
    open_application,
    close_application,
    install_application,
)


# =========================================================
# APPLICATION CHECK
# =========================================================

def tool_is_app_installed(app_name):

    try:

        result = find_application(
            app_name
        )

        if not isinstance(result, dict):
            return {
                "installed": bool(result)
            }

        return result

    except Exception as e:

        return {
            "installed": False,
            "error": str(e),
        }


# =========================================================
# OPEN APP
# =========================================================

def tool_open_app(app_name):

    try:

        result = open_application(
            app_name
        )

        if isinstance(result, dict):
            return result

        return {
            "success": bool(result),
            "app": app_name,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# CLOSE APP
# =========================================================

def tool_close_app(app_name):

    try:

        result = close_application(
            app_name
        )

        if isinstance(result, dict):
            return result

        return {
            "success": bool(result),
            "app": app_name,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# INSTALL APP
# =========================================================

def tool_install_app(app_name):

    try:

        result = install_application(
            app_name
        )

        if isinstance(result, dict):
            return result

        return {
            "success": bool(result),
            "app": app_name,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# CREATE PYTHON SCRIPT
# =========================================================

def tool_create_script(code):

    from agent.script_engine import save_script

    try:

        path = save_script(code)

        return {
            "success": True,
            "path": str(path),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# RUN PYTHON SCRIPT
# =========================================================

def tool_run_script(script_path):

    from agent.script_engine import run_script

    try:

        return run_script(
            script_path
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# EXECUTE PYTHON
# =========================================================

def tool_execute_python(
    code,
    packages=None,
):

    from agent.script_engine import (
        execute_python,
    )

    try:

        return execute_python(
            code,
            packages=packages,
        )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }