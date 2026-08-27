import json
import re
from pathlib import Path


# =========================================================
# MEMORY CONFIGURATION
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

MEMORY_FILE = (
    PROJECT_DIR / "memory.json"
)


# =========================================================
# DEFAULT MEMORY
# =========================================================

DEFAULT_MEMORY = {
    "user": {
        "name": "Eran",
    },
    "facts": {},
}


# =========================================================
# LOAD MEMORY
# =========================================================

def load_memory():

    if not MEMORY_FILE.exists():

        memory = {
            "user": {
                "name": "Eran",
            },
            "facts": {},
        }

        save_memory(
            memory
        )

        return memory

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict,
        ):
            return {
                "user": {
                    "name": "Eran",
                },
                "facts": {},
            }

        # -------------------------------------------------
        # Make sure required sections exist
        # -------------------------------------------------

        if not isinstance(
            data.get("user"),
            dict,
        ):
            data["user"] = {}

        if not isinstance(
            data.get("facts"),
            dict,
        ):
            data["facts"] = {}

        # -------------------------------------------------
        # Default user name
        # -------------------------------------------------

        if not data["user"].get(
            "name"
        ):
            data["user"]["name"] = "Eran"

        return data

    except (
        json.JSONDecodeError,
        OSError,
        Exception,
    ):

        # Do NOT crash Jarvis because of
        # a corrupted memory file.

        return {
            "user": {
                "name": "Eran",
            },
            "facts": {},
        }


# =========================================================
# SAVE MEMORY
# =========================================================

def save_memory(
    memory,
):

    try:

        MEMORY_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -------------------------------------------------
        # Write to temporary file first.
        #
        # This helps prevent a partially-written
        # memory.json if the process is interrupted.
        # -------------------------------------------------

        temp_file = MEMORY_FILE.with_suffix(
            ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                memory,
                file,
                ensure_ascii=False,
                indent=4,
            )

            file.flush()

        temp_file.replace(
            MEMORY_FILE
        )

        return True

    except Exception as e:

        print(
            f"⚠️ Could not save memory: {e}"
        )

        return False


# =========================================================
# REMEMBER
# =========================================================

def remember(
    key,
    value,
):

    key = str(
        key or ""
    ).strip()

    value = str(
        value or ""
    ).strip()

    if not key or not value:
        return False

    memory = load_memory()

    if "facts" not in memory:
        memory["facts"] = {}

    # -----------------------------------------------------
    # Normalize common keys
    # -----------------------------------------------------

    normalized_key = key.lower().strip()

    key_aliases = {
        "my age": "age",
        "age": "age",
        "my favorite game": "favorite game",
        "favorite game": "favorite game",
        "favourite game": "favorite game",
        "my favorite color": "favorite color",
        "favorite color": "favorite color",
        "favourite color": "favorite color",
    }

    normalized_key = key_aliases.get(
        normalized_key,
        normalized_key,
    )

    # -----------------------------------------------------
    # Store
    # -----------------------------------------------------

    memory["facts"][
        normalized_key
    ] = value

    return save_memory(
        memory
    )


# =========================================================
# FORGET
# =========================================================

def forget(
    key,
):

    key = str(
        key or ""
    ).strip().lower()

    if not key:
        return False

    memory = load_memory()

    facts = memory.get(
        "facts",
        {},
    )

    if key in facts:

        del facts[key]

        return save_memory(
            memory
        )

    return False


# =========================================================
# GET MEMORY
# =========================================================

def get_memory():

    return load_memory()


# =========================================================
# GET FACT
# =========================================================

def get_memory_value(
    key,
    default=None,
):

    memory = load_memory()

    facts = memory.get(
        "facts",
        {},
    )

    key = str(
        key or ""
    ).strip().lower()

    return facts.get(
        key,
        default,
    )


# =========================================================
# MEMORY → TEXT
# =========================================================

def memory_as_text():

    memory = load_memory()

    lines = []

    # -----------------------------------------------------
    # USER
    # -----------------------------------------------------

    user = memory.get(
        "user",
        {},
    )

    name = user.get(
        "name"
    )

    if name:

        lines.append(
            f"The user's name is {name}."
        )

    # -----------------------------------------------------
    # FACTS
    # -----------------------------------------------------

    facts = memory.get(
        "facts",
        {},
    )

    for key, value in facts.items():

        if key == "age":

            lines.append(
                f"The user's age is {value}."
            )

        elif key == "favorite game":

            lines.append(
                f"The user's favorite game is {value}."
            )

        elif key == "favorite color":

            lines.append(
                f"The user's favorite color is {value}."
            )

        elif key == "statement":

            lines.append(
                f"The user told you: {value}."
            )

        else:

            lines.append(
                f"The user told you that "
                f"{key} is {value}."
            )

    if not lines:

        return "No stored memories."

    return "\n".join(
        lines
    )


# =========================================================
# PARSE REMEMBER COMMAND
# =========================================================

def parse_remember_command(
    text,
):

    text = str(
        text or ""
    ).strip()

    if not text:
        return None

    # -----------------------------------------------------
    # Remove final punctuation
    # -----------------------------------------------------

    cleaned = text.rstrip(
        " .!?"
    )

    # =====================================================
    # REMEMBER MY X IS Y
    #
    # Examples:
    #
    # Remember my age is 13
    # Remember my favorite game is Fortnite
    # Remember my favorite color is blue
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?my\s+(.+?)\s+is\s+(.+)$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        key = match.group(
            1
        ).strip()

        value = match.group(
            2
        ).strip()

        return {
            "key": key,
            "value": value,
        }

    # =====================================================
    # REMEMBER THAT I'M X YEARS OLD
    #
    # Example:
    #
    # Remember that I'm 13 years old
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?i['’]m\s+(\d+)\s+years?\s+old$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        return {
            "key": "age",
            "value": match.group(1),
        }

    # =====================================================
    # REMEMBER THAT I AM X YEARS OLD
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?i\s+am\s+(\d+)\s+years?\s+old$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        return {
            "key": "age",
            "value": match.group(1),
        }

    # =====================================================
    # REMEMBER I'M X
    #
    # Example:
    #
    # Remember I'm 13
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?i['’]m\s+(\d+)$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        return {
            "key": "age",
            "value": match.group(1),
        }

    # =====================================================
    # REMEMBER I AM X
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?i\s+am\s+(\d+)$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        return {
            "key": "age",
            "value": match.group(1),
        }

    # =====================================================
    # REMEMBER THAT I ...
    #
    # Example:
    #
    # Remember that I love Fortnite
    #
    # Stored as a general statement.
    # =====================================================

    match = re.match(
        r"^remember\s+(?:that\s+)?i\s+(.+)$",
        cleaned,
        re.IGNORECASE,
    )

    if match:

        statement = match.group(
            1
        ).strip()

        if statement:

            return {
                "key": "statement",
                "value": statement,
            }

    return None


# =========================================================
# HANDLE MEMORY COMMAND
# =========================================================

def handle_memory_command(
    text,
):

    parsed = parse_remember_command(
        text
    )

    if not parsed:
        return None

    key = str(
        parsed.get(
            "key",
            "",
        )
    ).strip()

    value = str(
        parsed.get(
            "value",
            "",
        )
    ).strip()

    if not key or not value:
        return None

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    success = remember(
        key,
        value,
    )

    if not success:

        return (
            "I understood that you wanted me "
            "to remember it, but I couldn't save "
            "the memory."
        )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    normalized_key = key.lower().strip()

    if normalized_key == "age":

        return (
            f"Got it. I'll remember that "
            f"you are {value} years old."
        )

    if normalized_key == "statement":

        return (
            f"Got it. I'll remember that "
            f"you {value}."
        )

    return (
        f"Got it. I'll remember that "
        f"your {key} is {value}."
    )


# =========================================================
# CHECK WHETHER TEXT IS A MEMORY COMMAND
# =========================================================

def is_memory_command(
    text,
):

    return (
        parse_remember_command(
            text
        )
        is not None
    )