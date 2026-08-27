import webbrowser
from urllib.parse import quote


def search_web(query):
    """
    Opens Google and searches for the requested query.
    """

    if not query:
        return (
            False,
            "I don't know what you want me to search for."
        )

    url = (
        "https://www.google.com/search?q="
        + quote(query)
    )

    try:
        webbrowser.open(url)

        return (
            True,
            f"Searching the web for {query}."
        )

    except Exception as e:

        print(f"❌ Web search error: {e}")

        return (
            False,
            "I couldn't open the web search."
        )