import json
import requests


# =========================================================
# SETTINGS
# =========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODEL = "qwen3:1.7b"

TIMEOUT = 120


# =========================================================
# OLLAMA
# =========================================================

def ask_ollama(
    messages,
    temperature=0.1,
):
    """
    Send a request to Ollama.

    Returns the assistant text.
    """

    payload = {
        "model": MODEL,

        "messages": messages,

        "stream": False,

        # Qwen3 supports disabling thinking.
        "think": False,

        # Ask Ollama for JSON output.
        "format": "json",

        "options": {
            "temperature": temperature,
        },
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        message = data.get(
            "message",
            {},
        )

        content = message.get(
            "content",
            "",
        )

        return str(content).strip()

    except requests.exceptions.ConnectionError:

        raise RuntimeError(
            "Ollama is not running. "
            "Please start Ollama and try again."
        )

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Ollama took too long to respond."
        )

    except Exception as e:

        raise RuntimeError(
            f"Ollama error: {e}"
        )


# =========================================================
# JSON
# =========================================================

def ask_ollama_json(
    messages,
    temperature=0.1,
):
    """
    Ask Ollama and parse its response as JSON.
    """

    content = ask_ollama(
        messages,
        temperature=temperature,
    )

    if not content:

        raise RuntimeError(
            "Ollama returned an empty response."
        )

    # -----------------------------------------------------
    # Remove markdown fences if model accidentally adds them
    # -----------------------------------------------------

    content = content.strip()

    if content.startswith("```"):

        lines = content.splitlines()

        if lines:

            lines = lines[1:]

        if lines and lines[-1].strip() == "```":

            lines = lines[:-1]

        content = "\n".join(lines).strip()

    # -----------------------------------------------------
    # Parse JSON
    # -----------------------------------------------------

    try:

        return json.loads(content)

    except json.JSONDecodeError:

        # Try extracting the first JSON object.
        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end != -1:

            candidate = content[
                start:end + 1
            ]

            try:

                return json.loads(
                    candidate
                )

            except Exception:
                pass

        raise RuntimeError(
            "Ollama returned invalid JSON:\n"
            + content
        )