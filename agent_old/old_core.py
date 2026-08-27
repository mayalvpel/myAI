import time
import re
import ollama

from agent.tools_old import (
    open_application,
    youtube_search,
    web_search,
    spotify_play,

    save_memory,
    search_memory,

    create_code_file,
    read_code_file,
    write_code_file,
    open_code_in_vscode,
    run_python_file,
    list_project_files,
)

# =========================================================
# SETTINGS
# =========================================================

MODEL = "qwen3:1.7b"

MAX_STEPS = 10
LAST_CODE_FILE = None

# =========================================================
# TOOLS
# =========================================================

TOOLS = [
    open_application,
    youtube_search,
    web_search,
    spotify_play,

    save_memory,
    search_memory,

    create_code_file,
    read_code_file,
    write_code_file,
    open_code_in_vscode,
    run_python_file,
    list_project_files,
]

AVAILABLE_FUNCTIONS = {

    "open_application":
        open_application,

    "youtube_search":
        youtube_search,

    "web_search":
        web_search,

    "spotify_play":
        spotify_play,

    "save_memory":
        save_memory,

    "search_memory":
        search_memory,

    "create_code_file":
        create_code_file,

    "read_code_file":
        read_code_file,

    "write_code_file":
        write_code_file,

    "open_code_in_vscode":
        open_code_in_vscode,

    "run_python_file":
        run_python_file,

    "list_project_files":
        list_project_files,
}

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are JARVIS.

Your name is JARVIS.

Never call yourself Nova.

You are a local AI assistant, coding assistant,
computer assistant and autonomous agent.

You have two major capabilities:

1. You can reason, answer questions and GENERATE CODE
   directly using your language model.

2. You can interact with the user's Windows computer
   through tools.

Tools are optional.

Do NOT use a tool unless the task actually requires
interaction with the computer, files, Spotify, web,
YouTube or memory.

=========================================================
CODE GENERATION
=========================================================

---

CODE AND SCRIPT EXECUTION:

You are a coding assistant AND an autonomous computer agent.

You can create, modify, read and execute Python scripts
inside the project directory.

Your code tools are:

create_code_file
read_code_file
write_code_file
open_code_in_vscode
run_python_file
list_project_files

IMPORTANT:

When the user asks you to CREATE a script or file,
use create_code_file.

When the user asks you to MODIFY an existing script,
use read_code_file first, then write_code_file.

When the user asks you to RUN a Python script,
use run_python_file.

When the user asks you to OPEN a project file in VS Code,
use open_code_in_vscode.

---

AUTONOMOUS SCRIPT FALLBACK:

If the user asks you to perform an action that cannot be
performed directly by one of the available tools, but the
action can reasonably be performed by a Python script:

DO NOT say that you cannot do it.

Instead:

1. Understand what the user wants.
2. Generate a Python script that performs the requested action.
3. Create the script using create_code_file.
4. Run the script using run_python_file.
5. Inspect the execution result.
6. If the script fails, diagnose the error.
7. Fix the script using write_code_file.
8. Run it again.
9. Continue until the task succeeds or genuinely cannot
   be completed.

The script must be created inside the project directory.

Use a descriptive filename.

For example:

User:
"Check my external IP."

If there is no direct tool for checking the external IP:

Create a Python script such as:

get_external_ip.py

The script should perform the operation and print the result.

Then execute it using:

run_python_file

Do not merely give the user the Python code.

Actually create and run the script.

---

ANOTHER EXAMPLE:

User:
"Check whether example.com is online."

If no direct web-status tool exists:

1. Create a Python script.
2. Use an appropriate Python HTTP library.
3. Check the website.
4. Print a short result.
5. Run the script.
6. Return the result.

---

ANOTHER EXAMPLE:

User:
"Calculate the SHA256 hash of test.txt."

If no direct tool exists:

Create a Python script that performs the calculation,
run it, inspect the result, and return the hash.

---

IMPORTANT:

Do not create a script when an existing tool can perform
the task directly.

For example:

"Play music" -> use spotify_play.

"Search YouTube" -> use youtube_search.

"Open VS Code" -> use open_code_in_vscode.

"Run test.py" -> use run_python_file.

Only use the script fallback when no suitable existing
tool can perform the requested operation.

---

SCRIPT EXECUTION:

When executing a generated script:

Do not stop after creating the file.

The task is NOT complete until the script has been executed.

After execution:

- If STATUS: SUCCESS -> return the useful output.
- If STATUS: FAILED -> inspect the error and fix the script.
- If execution times out -> inspect the script before retrying.

Never claim that a task succeeded unless a tool confirms it.

---

FINAL ANSWERS:

When a script produces a useful result, return only the
useful result unless the user asks for an explanation.

Do not repeat the entire script.

Do not describe your internal reasoning.

Do not say:

"I cannot do that."

if the task can reasonably be implemented using a script.

Do not expose internal tool calls.

Do not expose internal reasoning.

Do not output:

"Final Answer:"

Do not output:

"<think>"

Do not output:

"Thinking..."

---

CODE GENERATION:

If the user only asks for code, generate the code.

If the user asks you to create and execute something,
actually create and execute it.

For example:

User:
"Write a Python script that prints Hello World."

Generate the code directly if the user only wants the code.

User:
"Create a Python file called hello.py that prints Hello World."

Use create_code_file.

User:
"Run hello.py."

Use run_python_file.

User:
"Create and run a script that checks my external IP."

Create the script, run it, inspect the result, and return
only the external IP.

Your name is JARVIS.

Never call yourself Nova.

You are controlling a Windows computer and have access
to tools for applications, Spotify, YouTube, web search
and long-term memory.

You are an autonomous agent with access to tools.

Your job:

1. Understand the CURRENT user request.
2. Decide whether a tool is required.
3. Use the correct tool.
4. Inspect the tool result.
5. Continue if another tool is necessary.
6. Only provide the final answer when the task is complete.

IMPORTANT:

The CURRENT user message always has priority.

Never reuse a previous tool call or previous tool argument
unless the user explicitly asks you to.

Never invent tool arguments.

Never invent facts.

Never claim that something happened unless a tool confirms it.

Do not expose internal reasoning.

Be concise, calm and professional.

Use natural British-style English.

---

MEMORY:

Long-term memory contains facts explicitly saved by the user.

If the current request asks about a fact that may be stored
in memory, search memory before answering.

Examples:

"Who is your creator?"
"Who is your programmer?"
"What is my project called?"
"What is the project name?"
"What do you remember about my project?"

Never answer these from your own model knowledge if the
information may exist in memory.

If memory provides an answer, use the memory result.

If no relevant memory exists, say that you do not have
that information stored.

Do not invent a person, project name, preference or fact.

When memory contains multiple values for the same fact,
prefer the newest relevant value.

Do not expose database formatting such as:

[project]

Do not say:

"I found the following in my memory."

Instead answer naturally.

Example:

Memory:
[project] The project name is Jarvis.

Answer:

"The project is called Jarvis."

Example:

Memory:
[general] Your programmer is Maya.

Answer:

"My programmer is Maya."

---

MEMORY SAVING:

When the user explicitly asks you to remember something,
save the actual information.

Example:

"Remember that your programmer is Maya."

The information is:

"Your programmer is Maya."

Do not save meaningless placeholders.

Do not save "/no_think".

Do not save empty or incomplete fragments.

---

UNCLEAR REQUESTS:

If the request is incomplete or unclear:

DO NOT guess.

DO NOT reuse a previous request.

DO NOT perform a random web search.

Ask the user to clarify.

Example:

User:
"No, not..."

Answer:

"What would you like me to do instead?"

---

TOOLS:

open_application:
Use when the user asks to open an application.

youtube_search:
Use when the user explicitly asks to search YouTube.

web_search:
Use when the user explicitly asks to search the web.

save_memory:
Use for explicit memory requests.

search_memory:
Use when a remembered fact may answer the current request.

Never mention tool names to the user.

spotify_play:
Use when the user asks to play music, a song, an artist,
or a track on Spotify.

Examples:

User:
"play Blinding Lights"

Correct tool call:

spotify_play(
    song="Blinding Lights"
)

User:
"play Imagine Dragons on Spotify"

Correct tool call:

spotify_play(
    song="Imagine Dragons"
)

IMPORTANT:

If the user says "play", "listen to", or "put on"
followed by a song or artist, do NOT use open_application.

Do NOT treat the song name as an application.

Use spotify_play.


CODE GENERATION AND CODE TOOLS:

You are a coding assistant.

You can generate code directly when the user only asks
for code or an explanation.

However, when the user asks you to CREATE, WRITE, SAVE,
UPDATE, MODIFY, EDIT, RUN or OPEN a code file on the
computer, you MUST use the appropriate code tool.

Available code tools:

create_code_file
read_code_file
write_code_file
open_code_in_vscode
run_python_file
list_project_files

IMPORTANT:

If the user asks to CREATE A FILE, do not merely return
the code in your response.

You MUST create the actual file using create_code_file.

Example:

User:
"Create a Python file called hellopy that prints hello world."

You MUST use:

create_code_file(
    path="hellopy.py",
    content="print(\"Hello World\")"
)

Then wait for the tool result.

Only after the tool confirms success should you tell the
user that the file was created.

---

If the user asks to MODIFY or UPDATE an existing file:

1. Use read_code_file first.
2. Understand the existing code.
3. Generate the required changes.
4. Use write_code_file to save the updated file.
5. Only report success after the tool confirms it.

---

If the user asks to RUN a Python file:

Use run_python_file.

Do not merely explain how to run it.

---

If the user asks to OPEN a file or project in VS Code:

Use open_code_in_vscode.

---

If the user asks to LIST project files:

Use list_project_files.

---

If the user only asks:

"Write me a Python script that prints Hello World."

Then do NOT create a file.

Simply return the code.

---

CRITICAL RULE:

Creating code and creating a code FILE are different tasks.

"Write me code" = generate code in the answer.

"Create a file" = use create_code_file.

"Save this code" = use create_code_file or write_code_file.

"Edit this file" = read_code_file followed by write_code_file.

"Run this file" = run_python_file.

"Open this in VS Code" = open_code_in_vscode.

CODE DEBUGGING:

When a code execution tool reports an error:

1. Read the error carefully.
2. Do NOT merely explain the error.
3. Read the affected source file using read_code_file.
4. Determine the correct fix.
5. Modify the file using write_code_file.
6. Run the file again using run_python_file.
7. Repeat if necessary.
8. Only report success after the execution succeeds.

NEVER invent a fix without inspecting the source file.

NEVER claim that code was fixed unless write_code_file confirms it.

NEVER say that a colon should be added merely because a Python
syntax error occurred.

For example:

If the file contains:

Hello from Jarvis

and Python reports a SyntaxError, the correct fix is:

print("Hello from Jarvis")

The agent must actually write that fix to the file and run it again.

=========================================================
AUTONOMOUS CODE EXECUTION
=========================================================

You are not limited to the existing tools.

If the user asks you to perform an action that cannot
be completed using an existing specialised tool, determine
whether the action can be performed by writing and running
a program.

You have code tools that allow you to:

- create_code_file
- read_code_file
- write_code_file
- run_python_file
- open_code_in_vscode
- list_project_files

IMPORTANT:

If no specialised tool can perform the requested action,
and the task can reasonably be automated with Python,
you SHOULD use the code tools.

Do not tell the user that you cannot perform the task
merely because there is no specialised tool.

Instead:

1. Understand the requested action.
2. Determine whether an existing specialised tool can
   perform it.
3. If yes, use that tool.
4. If no, determine whether Python can perform it.
5. If Python can perform it:
   - Generate the required Python script.
   - Create the script using create_code_file.
   - Run it using run_python_file.
   - Inspect the result.
6. If execution fails:
   - Read the relevant file if necessary.
   - Identify the error.
   - Fix the code using write_code_file.
   - Run it again.
7. Continue until the task succeeds or it is genuinely
   impossible.
8. Only then provide the final answer.

Never claim that an action was completed unless a tool
or executed program confirms it.

=========================================================
CODE-FIRST FALLBACK
=========================================================

When using Python as a fallback, prefer small,
self-contained scripts.

Do not unnecessarily create large applications.

Use existing Python libraries when available.

If an external package is required, determine whether
it is already available before relying on it.

For simple tasks, prefer the Python standard library.

Examples:

User:
"Check my public IP."

If there is no dedicated IP tool:

→ create a Python script
→ obtain the public IP
→ run the script
→ return the result.

User:
"Check if google.com is online."

If there is no dedicated website-checking tool:

→ create a Python script
→ perform the HTTP request
→ run it
→ report the result.

User:
"Calculate the SHA256 hash of this file."

If there is no dedicated hash tool:

→ create a Python script
→ calculate the hash
→ run it
→ report the result.

User:
"Convert this JSON file to CSV."

If there is no dedicated conversion tool:

→ create a Python script
→ perform the conversion
→ run it
→ report the result.

Do not generate code merely to answer a normal
programming question.

Use code execution when the user is asking you to
actually perform an action on the computer.
"""

# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(text):
    """
    Normalise speech-to-text output.
    """

    text = str(text or "").strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# =========================================================
# DETECT MEMORY SAVE
# =========================================================

def detect_memory_save(text):

    text = normalize_text(text)

    if not text:
        return None

    patterns = [
        r"^remember that (.+)$",
        r"^remember (.+)$",
        r"^don't forget that (.+)$",
        r"^dont forget that (.+)$",
        r"^keep in mind that (.+)$",
        r"^save this[:\s]+(.+)$",
        r"^store this[:\s]+(.+)$",
    ]

    for pattern in patterns:

        match = re.match(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        content = match.group(1).strip()

        if not content:
            return None

        # -------------------------------------------------
        # Reject obviously incomplete speech
        # -------------------------------------------------

        incomplete = [
            "m-",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "that",
            "my",
            "your",
            "project name is",
            "programmer is",
            "creator is",
        ]

        if content.lower() in incomplete:
            return {
                "type": "incomplete"
            }

        # -------------------------------------------------
        # Determine category
        # -------------------------------------------------

        lower = content.lower()

        category = "general"

        if (
            "project" in lower
            or "project name" in lower
        ):
            category = "project"

        elif (
            "prefer" in lower
            or "preference" in lower
            or "like" in lower
        ):
            category = "preference"

        elif (
            "my name" in lower
            or "i am" in lower
            or "i'm" in lower
        ):
            category = "user"

        # -------------------------------------------------
        # Normalize project name
        # -------------------------------------------------

        project_match = re.search(
            r"project\s+name\s+(?:is|=)\s+(.+)",
            content,
            re.IGNORECASE
        )

        if project_match:

            project_name = (
                project_match
                .group(1)
                .strip()
                .rstrip(".")
            )

            if project_name:

                content = (
                    f"The project name is "
                    f"{project_name}."
                )

                category = "project"

        # -------------------------------------------------
        # Normalize creator
        # -------------------------------------------------

        creator_match = re.search(
            r"(?:your|my)\s+creator\s+(?:is|=)\s+(.+)",
            content,
            re.IGNORECASE
        )

        if creator_match:

            person = (
                creator_match
                .group(1)
                .strip()
                .rstrip(".")
            )

            if person:

                content = (
                    f"Your creator is {person}."
                )

                category = "general"

        # -------------------------------------------------
        # Normalize programmer
        # -------------------------------------------------

        programmer_match = re.search(
            r"(?:your|my)\s+programmer\s+(?:is|=)\s+(.+)",
            content,
            re.IGNORECASE
        )

        if programmer_match:

            person = (
                programmer_match
                .group(1)
                .strip()
                .rstrip(".")
            )

            if person:

                content = (
                    f"Your programmer is {person}."
                )

                category = "general"

        return {
            "type": "save",
            "content": content,
            "category": category
        }

    return None


# =========================================================
# DETECT MEMORY SEARCH
# =========================================================

def detect_memory_search(text):

    text = normalize_text(text)

    if not text:
        return None

    lower = text.lower()

    # =====================================================
    # PROJECT
    # =====================================================

    project_patterns = [
        r"\bwhat is my project\b",
        r"\bwhat's my project\b",
        r"\bwhat is the project\b",
        r"\bwhat's the project\b",
        r"\bwhat is the project name\b",
        r"\bwhat's the project name\b",
        r"\bwhat is my project name\b",
        r"\bwhat's my project name\b",
        r"\bwhat is our project\b",
        r"\bwhat's our project\b",
    ]

    for pattern in project_patterns:

        if re.search(
            pattern,
            lower
        ):

            return {
                "type": "search",
                "query": "project name"
            }

    # =====================================================
    # CREATOR
    # =====================================================

    creator_patterns = [
        r"\bwho is your creator\b",
        r"\bwho's your creator\b",
        r"\bwho created you\b",
        r"\bwho made you\b",
        r"\bwho is your maker\b",
        r"\bwho's your maker\b",
    ]

    for pattern in creator_patterns:

        if re.search(
            pattern,
            lower
        ):

            return {
                "type": "search",
                "query": "creator"
            }

    # =====================================================
    # PROGRAMMER
    # =====================================================

    programmer_patterns = [
        r"\bwho is your programmer\b",
        r"\bwho's your programmer\b",
        r"\bwho programmed you\b",
        r"\bwho is your developer\b",
        r"\bwho's your developer\b",
        r"\bwho developed you\b",
        r"\bwho wrote you\b",
    ]

    for pattern in programmer_patterns:

        if re.search(
            pattern,
            lower
        ):

            return {
                "type": "search",
                "query": "programmer"
            }

    # =====================================================
    # GENERAL MEMORY QUESTIONS
    # =====================================================

    general_patterns = [
        r"\bdo you remember\b",
        r"\bwhat do you remember\b",
        r"\bwhat have you remembered\b",
        r"\bwhat did i ask you to remember\b",
        r"\bwhat did i tell you to remember\b",
        r"\bwhat do you know about me\b",
    ]

    for pattern in general_patterns:

        if re.search(
            pattern,
            lower
        ):

            return {
                "type": "search",
                "query": text
            }

    return None


# =========================================================
# DETECT MEMORY INTENT
# =========================================================

def detect_memory_intent(text):

    save_intent = detect_memory_save(
        text
    )

    if save_intent:
        return save_intent

    search_intent = detect_memory_search(
        text
    )

    if search_intent:
        return search_intent

    return None


# =========================================================
# MEMORY ANSWER
# =========================================================

def format_memory_answer(
    result,
    query
):

    if not result:
        return (
            "I don't have that information "
            "stored in my memory."
        )

    if (
        result == "No relevant memory found."
        or result == "No memory found."
    ):
        return (
            "I don't have that information "
            "stored in my memory."
        )

    # -----------------------------------------------------
    # Remove database category
    # -----------------------------------------------------

    lines = []

    for raw_line in result.splitlines():

        line = re.sub(
            r"^\[[^\]]+\]\s*",
            "",
            raw_line.strip()
        )

        if line:
            lines.append(line)

    if not lines:
        return (
            "I don't have that information "
            "stored in my memory."
        )

    query_lower = query.lower()

    # =====================================================
    # CREATOR
    # =====================================================

    if "creator" in query_lower:

        for line in lines:

            match = re.search(
                r"your creator is\s+(.+?)[.]?$",
                line,
                re.IGNORECASE
            )

            if match:

                person = (
                    match.group(1)
                    .strip()
                    .rstrip(".")
                )

                return (
                    f"My creator is {person}."
                )

    # =====================================================
    # PROGRAMMER
    # =====================================================

    if "programmer" in query_lower:

        for line in lines:

            match = re.search(
                r"your programmer is\s+(.+?)[.]?$",
                line,
                re.IGNORECASE
            )

            if match:

                person = (
                    match.group(1)
                    .strip()
                    .rstrip(".")
                )

                return (
                    f"My programmer is {person}."
                )

    # =====================================================
    # PROJECT
    # =====================================================

    if "project" in query_lower:

        for line in lines:

            match = re.search(
                r"project name is\s+(.+?)[.]?$",
                line,
                re.IGNORECASE
            )

            if match:

                project = (
                    match.group(1)
                    .strip()
                    .rstrip(".")
                )

                return (
                    f"The project is called {project}."
                )

    # =====================================================
    # FALLBACK
    # =====================================================

    # Return the newest relevant memory rather than
    # dumping the database to the user.

    return lines[0]


# =========================================================
# HANDLE MEMORY
# =========================================================

def handle_memory_intent(
    intent
):

    if intent["type"] == "save":

        print(
            f"📦 Memory: "
            f"{intent['content']}"
        )

        result = save_memory(
            content=intent["content"],
            category=intent["category"]
        )

        print(
            f"📤 Result: {result}"
        )

        if str(result).startswith("ERROR:"):

            return (
                "I was unable to save "
                "that information."
            )

        return (
            "I've saved that information."
        )

    # =====================================================
    # INCOMPLETE
    # =====================================================

    if intent["type"] == "incomplete":

        return (
            "I didn't catch the complete information. "
            "Please tell me what you would like me to remember."
        )

    # =====================================================
    # SEARCH
    # =====================================================

    if intent["type"] == "search":

        query = intent["query"]

        print(
            f"🔎 Memory query: {query}"
        )

        result = search_memory(
            query=query
        )

        print(
            f"📤 Result: {result}"
        )

        return format_memory_answer(
            result,
            query
        )

    return None

# =========================================================
# CODE FILE INTENT
# =========================================================

def detect_code_file_intent(text):

    text = normalize_text(text)

    if not text:
        return None

    lower = text.lower()

    create_patterns = [
        r"\bcreate\b.*\bfile\b",
        r"\bmake\b.*\bfile\b",
        r"\bwrite\b.*\bfile\b",
        r"\bsave\b.*\bfile\b",
        r"\bcreate\b.*\bscript\b",
        r"\bmake\b.*\bscript\b",
        r"\bcreate\b.*\.py\b",
        r"\bmake\b.*\.py\b",
        r"\bwrite\b.*\.py\b",
    ]

    for pattern in create_patterns:

        if re.search(pattern, lower):

            return {
                "type": "create_file"
            }

    return None


# =========================================================
# GENERATE CODE FOR FILE
# =========================================================

# =========================================================
# GENERATE CODE FOR FILE
# =========================================================

def generate_code_for_file(user_request: str):

    prompt = f"""
You are a code generation engine.

The user wants to create a source code file.

User request:

{user_request}

Generate the COMPLETE contents of the requested file.

CRITICAL RULES:

1. Return ONLY valid source code.
2. Do NOT return Markdown.
3. Do NOT use ``` fences.
4. Do NOT explain anything.
5. Do NOT describe the code.
6. The result must be directly executable/savable as the requested file.
7. Follow the user's requested behaviour exactly.

For example, if the user asks for a Python file that prints:

Hello from Jarvis

the output MUST be:

print("Hello from Jarvis")

NOT:

Hello from Jarvis

Return ONLY the file contents.
"""

    try:

        response = ollama.chat(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate valid source code only."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            think=False,
            options={
                "temperature": 0.0,
                "num_ctx": 8192,
                "num_predict": 4096
            }
        )

        code = (
            response.message.content
            or ""
        ).strip()

        # -------------------------------------------------
        # Remove accidental markdown fences
        # -------------------------------------------------

        if code.startswith("```"):

            lines = code.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            code = "\n".join(
                lines
            ).strip()

        if not code:

            return (
                None,
                "ERROR: The AI generated empty code."
            )

        print(
            "📝 Generated code:"
        )

        print(
            code
        )

        return (
            code,
            None
        )

    except Exception as e:

        print(
            f"❌ Code generation error: {e}"
        )

        return (
            None,
            f"ERROR: Could not generate code: {e}"
        )

# =========================================================
# EXTRACT CODE FILE PATH
# =========================================================

def extract_code_file_path(text):

    text = normalize_text(text)

    # -----------------------------------------------------
    # Explicit filename
    # -----------------------------------------------------

    patterns = [

        r"\bcalled\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",

        r"\bnamed\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",

        r"\bfile\s+([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)",

        r"\b([A-Za-z0-9_.-]+\.py)\b",

        r"\b([A-Za-z0-9_.-]+\.js)\b",

        r"\b([A-Za-z0-9_.-]+\.ts)\b",

        r"\b([A-Za-z0-9_.-]+\.ps1)\b",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1)

    return None

# =========================================================
# RUN AGENT
# =========================================================

def run_agent(
    user_text: str
):

    user_text = normalize_text(
        user_text
    )

    if not user_text:

        return (
            "I didn't receive a request."
        )

    start_time = time.time()

    print(
        "🧠 Sending request to Nova Agent..."
    )

    # =====================================================
    # MEMORY ROUTER
    # =====================================================

    memory_intent = detect_memory_intent(
        user_text
    )

    if memory_intent:

        print(
            "🧠 Memory intent detected."
        )

        print(
            f"🧠 Type: "
            f"{memory_intent['type']}"
        )

        try:

            answer = handle_memory_intent(
                memory_intent
            )

        except Exception as e:

            print(
                f"❌ Memory error: {e}"
            )

            return (
                "I was unable to access "
                "my memory."
            )

        elapsed = (
            time.time()
            - start_time
        )

        print(
            f"⏱️ Memory time: "
            f"{elapsed:.2f}s"
        )

        return answer
        # =====================================================
    # CODE FILE ROUTER
    # =====================================================

    code_intent = detect_code_file_intent(
        user_text
    )

    if code_intent:

        print(
            "💻 Code file intent detected."
        )

        file_path = extract_code_file_path(
            user_text
        )

        if not file_path:

            return (
                "What would you like to name the file?"
            )

        print(
            f"📄 Target file: {file_path}"
        )

        # -------------------------------------------------
        # Generate source code
        # -------------------------------------------------

        code, error = generate_code_for_file(
            user_text
        )

        if error:

            print(
                f"❌ {error}"
            )

            return (
                "I couldn't generate the requested code."
            )

        print(
            "🧠 Code generated successfully."
        )

        # -------------------------------------------------
        # Create actual file
        # -------------------------------------------------

        try:

            global LAST_CODE_FILE

            result = create_code_file(
                path=file_path,
                content=code
            )

            if not str(result).startswith("ERROR:"):
                LAST_CODE_FILE = file_path

        except Exception as e:

            print(
                f"❌ File creation error: {e}"
            )

            return (
                "I generated the code, "
                "but I couldn't create the file."
            )

        print(
            f"📤 Result: {result}"
        )

        # -------------------------------------------------
        # Tool failed
        # -------------------------------------------------

        if str(result).startswith("ERROR:"):

            return (
                f"I couldn't create {file_path}. "
                f"{result}"
            )

        # -------------------------------------------------
        # Success
        # -------------------------------------------------

        return (
            f"Created {file_path} successfully."
        )
    # =====================================================
    # RUN LAST CODE FILE
    # =====================================================

    def detect_run_last_file(text):

        text = normalize_text(text)

        if not text:
            return False

        lower = text.lower()

        patterns = [
            r"^run it$",
            r"^run that$",
            r"^run the file$",
            r"^run this file$",
            r"^execute it$",
            r"^execute that$",
            r"^run it please$",
        ]

        for pattern in patterns:

            if re.search(
                pattern,
                lower
            ):
                return True

        return False

    # =====================================================
# RUN LAST CREATED CODE FILE
# =====================================================

    if detect_run_last_file(user_text):

        if not LAST_CODE_FILE:

            return (
                "I don't have a recently created code file to run."
            )

        print(
            f"▶️ Running last code file: "
            f"{LAST_CODE_FILE}"
        )

        try:

            result = run_python_file(
                path=LAST_CODE_FILE
            )

        except Exception as e:

            print(
                f"❌ Run error: {e}"
            )

            return (
                "I couldn't run the last code file."
            )

        print(
            f"📤 Result: {result}"
        )

        return result
    # =====================================================
    # NORMAL AGENT
    # =====================================================

    messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },

        {
            "role": "user",
            "content": user_text
        }

    ]

    for step in range(
        MAX_STEPS
    ):

        print(
            f"🧠 Agent step "
            f"{step + 1}/{MAX_STEPS}"
        )

        try:

            response = ollama.chat(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                think=False,
                options={
                    "temperature": 0.1,
                    "num_ctx": 8192,
                    "num_predict": 2048
                }
            )

        except Exception as e:

            print(
                f"❌ Ollama error: {e}"
            )

            return (
                "I was unable to communicate "
                "with the local AI model."
            )

        # =================================================
        # APPEND ASSISTANT MESSAGE
        # =================================================

        messages.append(
            response.message
        )

        tool_calls = (
            response.message.tool_calls
            or []
        )

        # =================================================
        # FINAL ANSWER
        # =================================================

        if not tool_calls:

            answer = (
                response.message.content
                or "Task completed."
            )

            answer = str(
                answer
            ).strip()

            # -------------------------------------------------
            # Protect against Qwen exposing its reasoning
            # -------------------------------------------------

            if "<think>" in answer:

                if "</think>" in answer:

                    answer = answer.split(
                        "</think>",
                        1
                    )[1].strip()

                else:

                    answer = answer.split(
                        "<think>",
                        1
                    )[0].strip()

            elapsed = (
                time.time()
                - start_time
            )

            print(
                f"⏱️ Agent time: "
                f"{elapsed:.2f}s"
            )

            return answer

        # =================================================
        # EXECUTE TOOLS
        # =================================================

        for call in tool_calls:

            name = call.function.name

            arguments = (
                call.function.arguments
                or {}
            )

            print(
                f"🔧 Tool: {name}"
            )

            print(
                f"📦 Arguments: {arguments}"
            )

            function = (
                AVAILABLE_FUNCTIONS.get(
                    name
                )
            )

            if function is None:

                result = (
                    f"ERROR: Unknown tool {name}"
                )

            else:

                try:

                    if name == "save_memory":

                        content = arguments.get(
                            "content",
                            ""
                        )

                        if not content:

                            result = (
                                "ERROR: "
                                "Missing memory content."
                            )

                        else:

                            result = function(
                                **arguments
                            )

                    elif name == "search_memory":

                        query = arguments.get(
                            "query",
                            ""
                        )

                        if not query:

                            result = (
                                "ERROR: "
                                "Missing memory query."
                            )

                        else:

                            result = function(
                                **arguments
                            )

                    else:

                        result = function(
                            **arguments
                        )

                except Exception as e:

                    result = (
                        "ERROR: Tool execution failed: "
                        f"{e}"
                    )

            print(
                f"📤 Result: {result}"
            )

            # -------------------------------------------------
            # IMPORTANT:
            # Each tool call gets its own tool result.
            # -------------------------------------------------

        if name == "run_python_file":

            result_text = str(result)

            if "STATUS: SUCCESS" in result_text:

                stdout_match = re.search(
                    r"STDOUT:\s*(.*?)(?:\n\nSTATUS: SUCCESS|$)",
                    result_text,
                    re.DOTALL
                )

                if stdout_match:

                    output = stdout_match.group(1).strip()

                    if output:
                        return output

                return "Done."

            # If execution failed, let the model inspect the error.
            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": result_text
            })

        else:

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": str(result)
            })

    # =====================================================
    # MAX STEPS
    # =====================================================

    elapsed = (
        time.time()
        - start_time
    )

    print(
        f"⏱️ Agent time: "
        f"{elapsed:.2f}s"
    )

    return (
        "I was unable to complete the task "
        "within the allowed number of steps."
    )


    