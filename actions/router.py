from actions.apps import (
    open_app,
    install_app
)

from actions.youtube import (
    search_youtube
)

from actions.web import (
    search_web
)


# =========================================================
# EXECUTE ACTION
# =========================================================

def execute_action(action_data):

    # =====================================================
    # VALIDATION
    # =====================================================

    if not isinstance(action_data, dict):

        return (
            False,
            "Invalid action.",
            None
        )

    action = action_data.get(
        "action",
        ""
    )

    target = action_data.get(
        "target",
        ""
    )

    # =====================================================
    # CHAT
    # =====================================================

    if action == "chat":

        response = action_data.get(
            "response",
            ""
        )

        if not response:
            response = "I'm here. How can I help?"

        return (
            True,
            response,
            None
        )

    # =====================================================
    # OPEN APPLICATION
    # =====================================================

    if action == "open_app":

        success, message, pending = open_app(
            target
        )

        return (
            success,
            message,
            pending
        )

    # =====================================================
    # INSTALL APPLICATION
    # =====================================================

    if action == "install_app":

        winget_id = action_data.get(
            "winget"
        )

        try:

            success, message = install_app(
                target,
                winget_id=winget_id
            )

            return (
                success,
                message,
                None
            )

        except TypeError:

            # Compatibility with an older
            # install_app(target) function

            success, message = install_app(
                target
            )

            return (
                success,
                message,
                None
            )

    # =====================================================
    # YOUTUBE SEARCH
    # =====================================================

    if action == "youtube_search":

        if not target:

            return (
                False,
                "I don't know what you want me to search for on YouTube.",
                None
            )

        success, message = search_youtube(
            target
        )

        return (
            success,
            message,
            None
        )

    # =====================================================
    # WEB SEARCH
    # =====================================================

    if action == "web_search":

        if not target:

            return (
                False,
                "I don't know what you want me to search for.",
                None
            )

        success, message = search_web(
            target
        )

        return (
            success,
            message,
            None
        )

    # =====================================================
    # SPOTIFY PLAY
    # =====================================================

    if action == "spotify_play":

        # אם כבר יש לך Spotify router/module
        # אפשר לחבר אותו כאן.
        #
        # כרגע אנחנו מחזירים הודעה ברורה
        # במקום לגרום ל-Nova לקרוס.

        return (
            False,
            "Spotify playback is not connected yet.",
            None
        )

    # =====================================================
    # SPOTIFY CONTROL
    # =====================================================

    if action == "spotify_control":

        command = target.lower().strip()

        if command not in [
            "pause",
            "resume",
            "next",
            "previous"
        ]:

            return (
                False,
                f"I don't know the Spotify command {target}.",
                None
            )

        return (
            False,
            "Spotify control is not connected yet.",
            None
        )

    # =====================================================
    # UNKNOWN ACTION
    # =====================================================

    return (
        False,
        f"I don't know how to perform {action}.",
        None
    )