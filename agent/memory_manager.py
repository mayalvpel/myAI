import json
from pathlib import Path


# =========================================================
# MEMORY DIRECTORY
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

MEMORY_DIRECTORY = (
    PROJECT_DIR / "memory"
)

MEMORY_FILE = (
    MEMORY_DIRECTORY / "user_profile.json"
)


# =========================================================
# DEFAULT MEMORY
# =========================================================

DEFAULT_MEMORY = {
    "user": {
        "name": "Eran",
        "age_group": "teenager",
        "interests": [
            "Fortnite"
        ]
    },

    "preferences": {},

    "facts": []
}


# =========================================================
# ENSURE MEMORY
# =========================================================

def ensure_memory_file():
    """
    Make sure the memory directory and JSON file exist.
    """

    MEMORY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not MEMORY_FILE.exists():

        save_memory(
            DEFAULT_MEMORY
        )

    return MEMORY_FILE


# =========================================================
# LOAD MEMORY
# =========================================================

def load_memory():
    """
    Load Jarvis persistent memory.
    """

    ensure_memory_file()

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):
            return DEFAULT_MEMORY.copy()

        return data

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):

        # If memory is corrupted,
        # restore the default structure.

        save_memory(
            DEFAULT_MEMORY
        )

        return DEFAULT_MEMORY.copy()


# =========================================================
# SAVE MEMORY
# =========================================================

def save_memory(memory):
    """
    Save persistent Jarvis memory.
    """

    MEMORY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = (
        MEMORY_FILE.with_suffix(
            ".tmp"
        )
    )

    try:

        with open(
            temporary_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                memory,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_file.replace(
            MEMORY_FILE
        )

        return True

    except OSError:
        return False


# =========================================================
# GET USER PROFILE
# =========================================================

def get_user_profile():
    memory = load_memory()

    return memory.get(
        "user",
        {},
    )


# =========================================================
# GET USER NAME
# =========================================================

def get_user_name():
    profile = get_user_profile()

    return str(
        profile.get(
            "name",
            "User",
        )
    )


# =========================================================
# GET INTERESTS
# =========================================================

def get_user_interests():
    profile = get_user_profile()

    interests = profile.get(
        "interests",
        [],
    )

    if not isinstance(
        interests,
        list,
    ):
        return []

    return interests


# =========================================================
# ADD INTEREST
# =========================================================

def add_user_interest(
    interest,
):
    interest = str(
        interest or ""
    ).strip()

    if not interest:
        return False

    memory = load_memory()

    user = memory.setdefault(
        "user",
        {},
    )

    interests = user.setdefault(
        "interests",
        [],
    )

    if interest not in interests:

        interests.append(
            interest
        )

    return save_memory(
        memory
    )


# =========================================================
# ADD FACT
# =========================================================

def add_user_fact(
    fact,
):
    fact = str(
        fact or ""
    ).strip()

    if not fact:
        return False

    memory = load_memory()

    facts = memory.setdefault(
        "facts",
        [],
    )

    if fact not in facts:

        facts.append(
            fact
        )

    return save_memory(
        memory
    )


# =========================================================
# SET PREFERENCE
# =========================================================

def set_user_preference(
    key,
    value,
):
    key = str(
        key or ""
    ).strip()

    if not key:
        return False

    memory = load_memory()

    preferences = memory.setdefault(
        "preferences",
        {},
    )

    preferences[key] = value

    return save_memory(
        memory
    )


# =========================================================
# BUILD MEMORY PROMPT
# =========================================================

def build_memory_prompt():
    """
    Convert persistent memory into a small,
    safe system-prompt section.
    """

    memory = load_memory()

    user = memory.get(
        "user",
        {},
    )

    name = user.get(
        "name",
        "User",
    )

    age_group = user.get(
        "age_group",
        "",
    )

    interests = user.get(
        "interests",
        [],
    )

    preferences = memory.get(
        "preferences",
        {},
    )

    facts = memory.get(
        "facts",
        [],
    )

    lines = []

    lines.append(
        "USER MEMORY:"
    )

    lines.append(
        f"- User's name: {name}"
    )

    if age_group:

        lines.append(
            f"- User age group: {age_group}"
        )

    if interests:

        lines.append(
            "- User interests: "
            + ", ".join(
                str(item)
                for item in interests
            )
        )

    if preferences:

        lines.append(
            "- User preferences:"
        )

        for key, value in preferences.items():

            lines.append(
                f"  - {key}: {value}"
            )

    if facts:

        lines.append(
            "- Known user facts:"
        )

        for fact in facts:

            lines.append(
                f"  - {fact}"
            )

    lines.append(
        ""
    )

    lines.append(
        "Use this memory naturally when relevant."
    )

    lines.append(
        "Do not mention the existence of the memory system "
        "unless the user asks."
    )

    lines.append(
        "Do not assume every request is related to the user's interests."
    )

    return "\n".join(
        lines
    )