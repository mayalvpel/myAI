import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "memory"
    / "nova.db"
)


def init_memory():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with sqlite3.connect(DB_PATH) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()


# =========================================================
# REMEMBER
# =========================================================

def remember(
    content: str,
    category: str = "general"
) -> str:

    init_memory()

    content = str(
        content
    ).strip()

    category = str(
        category
    ).strip().lower()

    if not content:

        return (
            "ERROR: Cannot save empty memory."
        )

    # =====================================================
    # PROJECT NAME
    # =====================================================

    if category == "project":

        # Remove previous project-name memories
        # when saving a new project name.

        if (
            "project name is" in content.lower()
        ):

            with sqlite3.connect(
                DB_PATH
            ) as conn:

                conn.execute(
                    """
                    DELETE FROM memories
                    WHERE category = ?
                    AND LOWER(content)
                    LIKE 'the project name is%'
                    """,
                    (
                        "project",
                    )
                )

                conn.execute(
                    """
                    INSERT INTO memories
                    (content, category, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        content,
                        category,
                        datetime.now().isoformat()
                    )
                )

                conn.commit()

            return "Memory saved."

    # =====================================================
    # NORMAL MEMORY
    # =====================================================

    with sqlite3.connect(
        DB_PATH
    ) as conn:

        conn.execute(
            """
            INSERT INTO memories
            (content, category, created_at)
            VALUES (?, ?, ?)
            """,
            (
                content,
                category,
                datetime.now().isoformat()
            )
        )

        conn.commit()

    return "Memory saved."


# =========================================================
# RECALL
# =========================================================

def recall(
    query: str,
    limit: int = 5
) -> str:

    init_memory()

    query = str(
        query
    ).strip()

    words = [

        word.strip().lower()

        for word in query.split()

        if len(
            word.strip()
        ) >= 3

    ]

    if not words:

        return "No memory found."

    # =====================================================
    # PROJECT NAME
    # =====================================================

    if (
        "project" in query.lower()
        or "project name" in query.lower()
    ):

        with sqlite3.connect(
            DB_PATH
        ) as conn:

            row = conn.execute(
                """
                SELECT content, category, created_at
                FROM memories
                WHERE category = 'project'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if row:

            content, category, created_at = row

            return (
                f"[{category}] {content}"
            )

        return (
            "No relevant memory found."
        )

    # =====================================================
    # GENERAL SEARCH
    # =====================================================

    conditions = " OR ".join(
        [
            "LOWER(content) LIKE ?"
            for _ in words
        ]
    )

    params = [
        f"%{word}%"
        for word in words
    ]

    params.append(
        limit
    )

    with sqlite3.connect(
        DB_PATH
    ) as conn:

        rows = conn.execute(
            f"""
            SELECT content, category, created_at
            FROM memories
            WHERE {conditions}
            ORDER BY id DESC
            LIMIT ?
            """,
            params
        ).fetchall()

    if not rows:

        return (
            "No relevant memory found."
        )

    result = []

    for content, category, created_at in rows:

        result.append(
            f"[{category}] {content}"
        )

    return "\n".join(
        result
    )