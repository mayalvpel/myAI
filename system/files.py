import shutil
from pathlib import Path


# =========================================================
# CREATE FOLDER
# =========================================================

def create_folder(
    path: str
):

    try:

        folder = Path(
            path
        ).expanduser().resolve()

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        return {
            "success": True,
            "path": str(folder),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# LIST FILES
# =========================================================

def list_files(
    path: str
):

    try:

        folder = Path(
            path
        ).expanduser().resolve()

        if not folder.exists():

            return {
                "success": False,
                "error": "Directory does not exist."
            }

        if not folder.is_dir():

            return {
                "success": False,
                "error": "Path is not a directory."
            }

        files = []

        for item in folder.iterdir():

            files.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "is_directory": item.is_dir(),
                    "size": (
                        item.stat().st_size
                        if item.is_file()
                        else None
                    ),
                }
            )

        return {
            "success": True,
            "files": files,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# COPY
# =========================================================

def copy_file(
    source: str,
    destination: str
):

    try:

        src = Path(
            source
        ).expanduser().resolve()

        dst = Path(
            destination
        ).expanduser().resolve()

        if not src.exists():

            return {
                "success": False,
                "error": "Source does not exist."
            }

        shutil.copy2(
            src,
            dst
        )

        return {
            "success": True,
            "source": str(src),
            "destination": str(dst),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# MOVE
# =========================================================

def move_file(
    source: str,
    destination: str
):

    try:

        src = Path(
            source
        ).expanduser().resolve()

        dst = Path(
            destination
        ).expanduser().resolve()

        if not src.exists():

            return {
                "success": False,
                "error": "Source does not exist."
            }

        shutil.move(
            str(src),
            str(dst)
        )

        return {
            "success": True,
            "source": str(src),
            "destination": str(dst),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# =========================================================
# DELETE
# =========================================================

def delete_file(
    path: str
):

    try:

        target = Path(
            path
        ).expanduser().resolve()

        if not target.exists():

            return {
                "success": False,
                "error": "Path does not exist."
            }

        if target.is_dir():

            return {
                "success": False,
                "error": (
                    "Refusing to delete a directory "
                    "with this tool."
                )
            }

        target.unlink()

        return {
            "success": True,
            "path": str(target),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }