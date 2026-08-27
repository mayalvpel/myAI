import os
import urllib.parse


def youtube_search(query):
    """
    Opens YouTube directly on search results.
    """

    if not query:
        return False, "I don't know what to search for."

    encoded_query = urllib.parse.quote_plus(query)

    url = f"https://www.youtube.com/results?search_query={encoded_query}"

    print(f"🔎 YouTube search: {query}")

    try:
        os.startfile(url)

        return (
            True,
            f"Searching YouTube for {query}."
        )

    except Exception as e:

        print(f"❌ YouTube error: {e}")

        return (
            False,
            "I couldn't search YouTube."
        )


def web_search(query):
    """
    Opens Google search results.
    """

    if not query:
        return False, "I don't know what to search for."

    encoded_query = urllib.parse.quote_plus(query)

    url = f"https://www.google.com/search?q={encoded_query}"

    print(f"🔎 Google search: {query}")

    try:

        os.startfile(url)

        return (
            True,
            f"Searching for {query}."
        )

    except Exception as e:

        print(f"❌ Browser error: {e}")

        return (
            False,
            "I couldn't perform the search."
        )