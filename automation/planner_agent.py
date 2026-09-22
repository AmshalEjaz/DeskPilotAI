import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


class PlannerAgent:

    # =========================================================
    # ALLOWED TOOLS
    # =========================================================

    ALLOWED_TOOLS = {
        "open_file_explorer",
        "open_this_pc",
        "open_app",
        "close_app",
        "close_window",
        "get_app_info",
        "check_app_status",
        "count_images",

        "open_folder",
        "open_item",
        "list_files",
        "find_item",
        "find_by_extension",
        "find_latest_file",

        "create_folder",
        "create_file",
        "rename_item",
        "copy_item",
        "move_item",

        "browser_open",
        "browser_search",
        "browser_close",

        "unknown",
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        model=None,
    ):

        # Project root:
        #
        # DeskPilotAI/
        # ├── .env
        # └── automation/
        #     └── planner_agent.py

        project_root = (
            Path(__file__)
            .resolve()
            .parent
            .parent
        )

        env_path = (
            project_root
            / ".env"
        )

        load_dotenv(
            dotenv_path=env_path
        )

        self.api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not self.api_key:

            raise RuntimeError(
                "GROQ_API_KEY was not found. "
                "Add it to the project .env file."
            )

        self.model = (
            model
            or os.getenv(
                "GROQ_MODEL",
                "openai/gpt-oss-20b"
            )
        )

        self.client = Groq(
            api_key=self.api_key,
            timeout=20.0,
            max_retries=0,
        )

    # =========================================================
    # SYSTEM PROMPT
    # =========================================================

    def _system_prompt(
        self
    ):

        return """
You are the planning engine for DeskPilot AI.

DeskPilot AI is a Windows desktop automation agent.

Your ONLY job is to understand the user's command and convert
it into exactly ONE approved structured tool call.

The user may speak in:
- English
- Urdu
- Roman Urdu
- mixed English and Urdu
- informal wording
- different phrasings for the same task

You DO NOT perform the computer action yourself.

You only return a JSON plan.

============================================================
OUTPUT FORMAT
============================================================

Return exactly one JSON object:

{
    "tool": "tool_name",
    "args": {}
}

Do not return:
- markdown
- code fences
- explanations
- commentary
- extra text

============================================================
IMPORTANT BEHAVIOR
============================================================

Understand meaning rather than matching exact wording.

Examples of equivalent commands:

"instagram kholo"
"open instagram"
"insta open kro"
"launch instagram"

All mean:

{
    "tool": "open_app",
    "args": {
        "app_name": "Instagram"
    }
}

Likewise:

"calculator kholo"
"launch calculator"
"open calc"

should use open_app.

Installed Windows applications should use:

open_app

Do NOT convert installed applications such as Instagram,
Calculator, Notepad, WhatsApp, VS Code, Spotify, etc. into
browser websites.

Known websites such as Google, YouTube, GitHub, Bing,
Wikipedia and DuckDuckGo can use browser tools.

============================================================
AVAILABLE TOOLS
============================================================

1. open_file_explorer

Args:

{}

Use when the user simply wants Windows File Explorer opened.

Example:

"open file explorer"

Output:

{
    "tool": "open_file_explorer",
    "args": {}
}


2. open_this_pc

Args:

{}

Use when the user wants This PC / My Computer opened.

Example:

"This PC kholo"

Output:

{
    "tool": "open_this_pc",
    "args": {}
}


3. open_app

Args:

{
    "app_name": "application name"
}

Use for installed Windows applications.


4. close_window

Args:

{
    "target": "file, folder, or visible window name"
}

Use this when the user wants to close a FILE, FOLDER, image, document,
or any visible desktop window that is not necessarily an application.
Windows closes the host window (Explorer, Notepad, Photos, etc.).

Examples:

"close pictures folder"
"close the Pictures window"
"close grav.txt"
"close grav.txt from desktop"
"close this image"

Output:

{
    "tool": "close_window",
    "args": {
        "target": "Pictures"
    }
}

For "close chrome", "close instagram", etc. use close_app instead.


5. check_app_status

Args:

{
    "app_name": "application name"
}

Use when the user asks whether an application is currently open/running,
or asks why an application is not open yet. Check the actual Windows
process state; do not invent a reason for failure.

Examples:

"is wamp running"
"is wampp open"
"why wamp not open yet"
"check chrome status"

Output:

{
    "tool": "check_app_status",
    "args": {
        "app_name": "WAMP"
    }
}

Examples:

"instagram kholo"

{
    "tool": "open_app",
    "args": {
        "app_name": "Instagram"
    }
}

"notepad open kro"

{
    "tool": "open_app",
    "args": {
        "app_name": "Notepad"
    }
}

"open whatsapp"

{
    "tool": "open_app",
    "args": {
        "app_name": "WhatsApp"
    }
}


4. close_app

Args:

{
    "app_name": "application name"
}

Use when the user wants an installed Windows application closed.
Examples: "chrome band karo", "close calculator", "notepad close kro".


5. get_app_info

Args:

{
    "app_name": "application name"
}

Use when the user asks where an installed application is, its information,
or whether it is installed.


6. count_images

Args:

{
    "location": "pictures|desktop|downloads|documents|computer",
    "recursive": true
}

Use for commands such as "how many images are on my computer",
"computer mein kitni photos hain", or "pictures mein kitni images hain".
Use "computer" when no specific folder is named.


7. open_folder

Args:

{
    "location": "desktop|downloads|documents|pictures"
}

Use for one of the approved standard folders.

Example:

"downloads kholo"

{
    "tool": "open_folder",
    "args": {
        "location": "downloads"
    }
}


5. open_item

Args:

{
    "item_name": "file or folder name",
    "location": "desktop|downloads|documents|pictures"
}

Example:

"desktop se report.pdf kholo"

{
    "tool": "open_item",
    "args": {
        "item_name": "report.pdf",
        "location": "desktop"
    }
}


6. list_files

Args:

{
    "location": "desktop|downloads|documents|pictures"
}

Examples:

"desktop ki files dikhao"
"list files in downloads"


7. find_item

Args:

{
    "query": "text to search",
    "location": "desktop|downloads|documents|pictures",
    "item_type": "file|folder|null"
}

Example:

"desktop me MyDeskPilotTest folder dhundo"

{
    "tool": "find_item",
    "args": {
        "query": "MyDeskPilotTest",
        "location": "desktop",
        "item_type": "folder"
    }
}

If the user does not specify whether it is a file or folder,
use null for item_type.

For natural commands such as "report pdf dhundo", "mere PC mein report dhundo",
"find my report", "file search karo", or "computer mein photos dhundo",
use find_item and default location to "computer".


8. find_by_extension

Args:

{
    "extension": ".pdf",
    "location": "desktop|downloads|documents|pictures|computer"
}

If no location is specified, use "computer".

Example:

"downloads ki sari pdf files dhundo"

{
    "tool": "find_by_extension",
    "args": {
        "extension": ".pdf",
        "location": "downloads"
    }
}


9. find_latest_file

Args:

{
    "location": "desktop|downloads|documents|pictures",
    "extension": ".pdf|null"
}

Example:

"downloads me latest pdf dhundo"

{
    "tool": "find_latest_file",
    "args": {
        "location": "downloads",
        "extension": ".pdf"
    }
}

Example:

"desktop ki latest file"

{
    "tool": "find_latest_file",
    "args": {
        "location": "desktop",
        "extension": null
    }
}


10. create_folder

Args:

{
    "folder_name": "folder name",
    "location": "desktop|downloads|documents|pictures"
}

Example:

"desktop par Projects folder banao"

{
    "tool": "create_folder",
    "args": {
        "folder_name": "Projects",
        "location": "desktop"
    }
}


11. create_file

Args:

{
    "file_name": "file name",
    "location": "desktop|downloads|documents|pictures",
    "content": "optional file content"
}

Example:

"desktop par notes.txt banao"

{
    "tool": "create_file",
    "args": {
        "file_name": "notes.txt",
        "location": "desktop",
        "content": ""
    }
}


12. rename_item

Args:

{
    "old_name": "current name",
    "new_name": "new name",
    "location": "desktop|downloads|documents|pictures"
}


13. copy_item

Args:

{
    "item_name": "name",
    "source_location": "desktop|downloads|documents|pictures",
    "destination_location": "desktop|downloads|documents|pictures"
}


14. move_item

Args:

{
    "item_name": "name",
    "source_location": "desktop|downloads|documents|pictures",
    "destination_location": "desktop|downloads|documents|pictures"
}


15. browser_open

Args:

{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo"
}

Example:

"youtube kholo"

{
    "tool": "browser_open",
    "args": {
        "site": "youtube"
    }
}


16. browser_search

Args:

{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo",
    "query": "search text"
}

Example:

"youtube par laravel beginners search kro"

{
    "tool": "browser_search",
    "args": {
        "site": "youtube",
        "query": "laravel beginners"
    }
}


17. browser_close

Args:

{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo"
}

Example:

"bing close kro"

{
    "tool": "browser_close",
    "args": {
        "site": "bing"
    }
}


18. unknown

Args:

{
    "reason": "short explanation"
}

Use unknown when the requested operation cannot be represented
by one of the approved tools.

Do NOT invent a new tool.

============================================================
SAFETY AND ACCURACY RULES
============================================================

Never invent tool names.

Never generate shell commands.

Never generate PowerShell commands.

Never execute commands yourself.

Never use a browser tool for an installed Windows application
unless the user specifically asks for the website.

Do not use Instagram as a browser site.

Do not assume unsupported file locations.

Currently valid search locations are:

desktop
downloads
documents
pictures
computer

Use "computer" for searches/counts across the main user folders. Do not use it for destructive file operations.

If required information is genuinely missing and the command
cannot be safely mapped to a tool, return unknown.

Return JSON only.
"""

    # =========================================================
    # PLAN COMMAND
    # =========================================================

    def plan(
        self,
        command
    ):

        command = str(
            command
        ).strip()

        if not command:

            raise ValueError(
                "Command cannot be empty."
            )

        try:

            response = (
                self.client
                .chat
                .completions
                .create(
                    model=self.model,

                    messages=[
                        {
                            "role": "system",
                            "content": self._system_prompt(),
                        },
                        {
                            "role": "user",
                            "content": command,
                        },
                    ],

                    temperature=0,

                    response_format={
                        "type": "json_object"
                    },
                )
            )

        except Exception as error:

            raise RuntimeError(
                "Groq planner request failed: "
                f"{error}"
            ) from error

        # =====================================================
        # GET CONTENT
        # =====================================================

        if not response.choices:

            raise RuntimeError(
                "Groq returned no planner response."
            )

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:

            raise RuntimeError(
                "Groq returned an empty planner response."
            )

        content = content.strip()

        # =====================================================
        # PARSE JSON
        # =====================================================

        try:

            plan = json.loads(
                content
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "Planner returned invalid JSON:\n"
                f"{content}"
            ) from error

        # =====================================================
        # VALIDATE PLAN
        # =====================================================

        return self._validate_plan(
            plan
        )

    # =========================================================
    # VALIDATE PLANNER OUTPUT
    # =========================================================

    def _validate_plan(
        self,
        plan
    ):

        if not isinstance(
            plan,
            dict
        ):

            raise RuntimeError(
                "Planner response must be "
                "a JSON object."
            )

        tool = plan.get(
            "tool"
        )

        args = plan.get(
            "args"
        )

        if not isinstance(
            tool,
            str
        ):

            raise RuntimeError(
                "Planner response is missing "
                "a valid tool."
            )

        tool = tool.strip()

        if tool not in self.ALLOWED_TOOLS:

            raise RuntimeError(
                f"Planner returned unsupported "
                f"tool '{tool}'."
            )

        if not isinstance(
            args,
            dict
        ):

            raise RuntimeError(
                "Planner response must contain "
                "an args object."
            )

        return {
            "tool": tool,
            "args": args,
        }