import webbrowser
from urllib.parse import quote


def search_youtube(query):
    """
    Opens YouTube and searches for the requested query.
    """

    if not query:
        return (
            False,
            "I don't know what you want me to search for."
        )

    url = (
        "https://www.youtube.com/results?search_query="
        + quote(query)
    )

    try:
        webbrowser.open(url)

        return (
            True,
            f"Searching YouTube for {query}."
        )

    except Exception as e:

        print(f"❌ YouTube error: {e}")

        return (
            False,
            "I couldn't open YouTube."
        )