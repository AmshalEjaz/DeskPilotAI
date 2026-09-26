import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


class PlannerAgent:

    
    # ALLOWED TOOLS
    

    ALLOWED_TOOLS = {
        "open_file_explorer",
        "open_this_pc",
        "recycle_bin",
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
        "check_running_apps",
        "get_window_info",
        "window_control",
        "minimize_all_windows",
        "restore_all_windows",
        "take_screenshot",
        "open_url",

        "unknown",
    }

    
    # INIT
    

    def __init__(
        self,
        model=None,
    ):


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

    
    # SYSTEM PROMPT
    

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


18. check_running_apps

Args:

{}

Use when the user asks to show/list currently open windows.
Examples: "show open windows", "open windows dikhao", "which windows are open".


19. get_window_info

Args:

{
    "target": "window name"
}

Use when the user asks whether a particular visible window is open.


20. window_control

Args:

{
    "target": "window name",
    "action": "minimize|maximize|restore|activate"
}

Use for commands such as:
"minimize DeskPilot AI"
"maximize Chrome"
"restore Notepad"
"switch to Chrome"


21. minimize_all_windows

Args:

{}

Use for "minimize all windows" / "sab windows minimize karo".


22. restore_all_windows

Args:

{}

Use for "restore all windows".


23. take_screenshot

Args:

{}

Use for "take a screenshot" / "screen shot le lo".


24. open_url

Args:

{
    "url": "https://example.com"
}

Use when the user provides a direct http/https URL and asks to open it.


25. unknown

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

    @staticmethod
    def _normalize_command_location(value):
        value = str(value or "").strip()
        drive = re.fullmatch(r"(?:([A-Za-z]):|([A-Za-z])\s+drive|drive\s+([A-Za-z]))", value, re.IGNORECASE)
        if drive:
            letter = next(group for group in drive.groups() if group)
            return f"{letter.upper()}:"
        return value

    def _repair_common_intent(self, command, plan):
        """Make obvious desktop intents deterministic after the LLM plan."""
        text = str(command or "").strip().lower()
        compact = re.sub(r"\s+", " ", text)

        # Direct URL opens should never fall through to file search.
        url_match = re.search(r"https?://\S+", compact, re.IGNORECASE)
        if url_match and re.search(r"\b(?:open|launch|visit|go to)\b", compact, re.IGNORECASE):
            return {"tool": "open_url", "args": {"url": url_match.group(0).rstrip(".,)\"'")}}

        # Window commands must be recognized before generic file search.
        if (re.search(r"\b(?:show|list|display|which|what)\b.*\b(?:open|opened|running)\s+windows?\b", compact, re.IGNORECASE)
                or re.search(r"\b(?:open|running)\s+windows?\b", compact, re.IGNORECASE)
                or re.search(r"\bwindows?\s+(?:open|opened|running)\b", compact, re.IGNORECASE)):

            return {"tool": "check_running_apps", "args": {}}

        # Common window actions are deterministic so they cannot fall through
        # to filename search (e.g. "show open windows").
        if re.search(r"\b(?:minimi[sz]e|minimiza|minimizar)\s+all\s+windows?\b|\bsab\s+windows?\s+(?:minimi[sz]e|chhoti)", compact, re.IGNORECASE):
            return {"tool": "minimize_all_windows", "args": {}}
        if re.search(r"\brestore\s+all\s+windows?\b|\bsab\s+windows?\s+(?:restore|wapas)", compact, re.IGNORECASE):
            return {"tool": "restore_all_windows", "args": {}}
        if re.search(r"\b(?:take|capture|make)\s+(?:a\s+)?screen\s*shot\b|\bscreen\s*shot\s+(?:le|lo|banao|do)", compact, re.IGNORECASE):
            return {"tool": "take_screenshot", "args": {}}

        window_action = re.search(
            r"\b(?P<action>minimi[sz]e|minimiza|minimizar|maximi[sz]e|maximiza|restore|switch|activate|focus)\s+(?:the\s+)?(?P<target>.+?)\s*$",
            compact,
            re.IGNORECASE,
        )
        if window_action and "window" not in window_action.group("target"):
            action = window_action.group("action").lower()
            action = "minimize" if action.startswith(("minimi", "minimiza", "minimizar")) else "maximize" if action.startswith(("maximi", "maximiza")) else action
            target = re.sub(r"^\s*(?:to|the)\s+", "", window_action.group("target").strip(), flags=re.IGNORECASE)
            target = re.sub(r"\s+(?:window|app|application)$", "", target, flags=re.IGNORECASE)
            # Do not steal explicit application-close/open commands.
            if not re.match(r"^(?:open|launch|close|quit|exit)\b", target, re.IGNORECASE):
                return {"tool": "window_control", "args": {"target": target, "action": action}}

        # Windows Recycle Bin is a special shell namespace, not a normal app
        # or filesystem search target. Handle it before the LLM plan is used.
        if re.search(r"\brecycle[ _-]?bin\b", compact, re.IGNORECASE):
            # One dedicated Recycle Bin tool handles open, count, empty, and close.
            # Close must be checked before the generic open fallback.
            if re.search(r"\b(?:close|shut|exit|band|band\s+kar|band\s+karo)\b", compact, re.IGNORECASE):
                action = "close"
            elif re.search(r"\b(?:empty|clear|clean|delete\s+all|remove\s+all|khali|saaf)\b", compact, re.IGNORECASE):
                action = "empty"
            elif re.search(r"\b(?:how many|count|number of|check|files?\s+are|folders?\s+are)\b", compact, re.IGNORECASE):
                action = "open_and_count" if re.search(r"\b(?:open|launch|kholo)\b", compact) else "count"
            else:
                action = "open"
            return {"tool": "recycle_bin", "args": {"action": action}}

        browser_sites = {
            "google": "google",
            "youtube": "youtube",
            "yt": "youtube",
            "github": "github",
            "bing": "bing",
            "wikipedia": "wikipedia",
            "duckduckgo": "duckduckgo",
        }

        # Browser close must use the dedicated browser worker so Chromium
        # disappears instead of leaving an about:blank window behind.
        for name, site in browser_sites.items():
            if (re.search(rf"\b(?:close|quit|exit|band|bnd)\b.*\b{re.escape(name)}\b", compact)
                    or re.search(rf"\b{re.escape(name)}\b.*\b(?:close|quit|exit|band|bnd)\b", compact)):
                return {"tool": "browser_close", "args": {"site": site}}

        # Browser search.
        search_match = re.match(
            r"^(?:open|go to|visit)?\s*(google|youtube|yt|github|bing|wikipedia|duckduckgo)"
            r"\s+(?:and\s+)?search(?:\s+for)?\s+(.+)$",
            compact,
            re.IGNORECASE,
        )
        if search_match:
            site = browser_sites[search_match.group(1).lower()]
            return {
                "tool": "browser_search",
                "args": {"site": site, "query": search_match.group(2).strip()},
            }

        # Browser open.
        for name, site in browser_sites.items():
            if re.match(
                rf"^(?:open|launch|go to|visit)\s+(?:the\s+)?{re.escape(name)}(?:\s+(?:website|site))?\s*$",
                compact,
                re.IGNORECASE,
            ):
                return {"tool": "browser_open", "args": {"site": site}}

        # Compound natural-language folder + item commands.
        # Examples: "go to Documents folder and open Laravel Notes" and
        # common typos such as "do to document folder and open intelgs".
        compound_open = re.match(
            r"^(?:go|do|open|visit)\s+(?:to\s+)?(?:the\s+)?"
            r"(?P<location>desktop|downloads?|documents?|pictures?|videos?)"
            r"(?:\s+folder)?\s+and\s+(?:open|launch|start|kholo)\s+"
            r"(?:the\s+)?(?P<query>.+?)\s*$",
            compact,
            re.IGNORECASE,
        )
        if compound_open:
            location = {
                "download": "downloads", "downloads": "downloads",
                "document": "documents", "documents": "documents",
                "picture": "pictures", "pictures": "pictures",
                "video": "videos", "videos": "videos",
                "desktop": "desktop",
            }[compound_open.group("location").lower()]
            return {
                "tool": "find_item",
                "args": {
                    "query": compound_open.group("query").strip(),
                    "location": location,
                    "item_type": None,
                    "open_result": True,
                },
            }

        # Common local-folder opens must be handled before the generic file
        # matcher below. Otherwise commands such as "open pictures folder"
        # can be mistaken for a file search.
        local_folder_locations = {
            "desktop": "desktop",
            "downloads": "downloads",
            "download": "downloads",
            "documents": "documents",
            "document": "documents",
            "pictures": "pictures",
            "picture": "pictures",
            "videos": "videos",
            "video": "videos",
        }
        folder_open_match = re.match(
            r"^(?:open|launch|go to|visit|kholo)\s+(?:the\s+)?(?P<location>desktop|downloads?|documents?|pictures?|videos?)(?:\s+folder)?$",
            compact,
            re.IGNORECASE,
        )
        if folder_open_match:
            location = local_folder_locations[folder_open_match.group("location").lower()]
            return {"tool": "open_folder", "args": {"location": location}}

        # Extension searches must be recognized before the generic "open
        # file" matcher. Without this, "open .txt files from desktop" can
        # be treated as a literal filename search.
        extension_location = (
            r"my computer|this pc|downloads?|documents?|pictures?|desktop|"
            r"destop|videos?|computer|pc|[A-Za-z]:(?:\s*drive)?|[A-Za-z]\s+drive|drive\s*[A-Za-z]"
        )
        extension_command = re.match(
            rf"^(?P<action>open|launch|show|display|find|search|locate)\s+"
            rf"(?P<all>all\s+)?(?:the\s+)?(?P<extension>\.?[A-Za-z0-9]{{1,8}})\s+"
            rf"(?:files?|documents?)\s+(?:from|in|on|inside|under)\s+(?:the\s+)?"
            rf"(?P<location>{extension_location})\s*$",
            compact,
            re.IGNORECASE,
        )
        if extension_command:
            ext = extension_command.group("extension").strip()
            if not ext.startswith("."):
                ext = "." + ext
            location = extension_command.group("location").strip()
            location_aliases = {
                "destop": "desktop", "desktop": "desktop",
                "download": "downloads", "downloads": "downloads",
                "document": "documents", "documents": "documents",
                "picture": "pictures", "pictures": "pictures",
                "video": "videos", "videos": "videos",
                "computer": "computer", "pc": "computer",
                "my pc": "computer", "my computer": "computer",
                "this pc": "computer",
            }
            location = location_aliases.get(location.lower(), location)
            if re.fullmatch(r"[A-Za-z]:?(?:\s*drive)?", location, re.IGNORECASE) or re.fullmatch(r"drive\s*[A-Za-z]", location, re.IGNORECASE):
                location = self._normalize_command_location(location)
            action = extension_command.group("action").lower()
            return {
                "tool": "find_by_extension",
                "args": {
                    "extension": ext,
                    "location": location,
                    "open_results": action in {"open", "launch"},
                },
            }

        # Files/folders/images/documents are windows, not installed apps.
        close_match = re.match(
            r"^(?:close|quit|exit|band|bnd)(?:\s+the)?\s+(.+)$",
            compact,
            re.IGNORECASE,
        )
        if close_match:
            target = close_match.group(1).strip()
            target = re.sub(
                r"\s+(?:from|in)\s+(?:the\s+)?(?:desktop|downloads?|documents?|pictures?)\s*$",
                "",
                target,
                flags=re.IGNORECASE,
            ).strip()
            filesystem_words = (
                r"(?:folder|directory|window|file|image|photo|document|pdf|txt|docx|xlsx|pptx|csv|jpg|jpeg|png|gif|webp|bmp|svg)"
            )
            if re.search(filesystem_words, target, re.IGNORECASE) or target.lower() in {
                "pictures", "downloads", "documents", "desktop", "this pc", "my pc", "file explorer"
            } or re.search(r"\.[a-z0-9]{1,6}$", target, re.IGNORECASE):
                target = re.sub(r"\s+(?:folder|directory|window)$", "", target, flags=re.IGNORECASE).strip()
                return {"tool": "close_window", "args": {"target": target}}

        # Direct file-open commands should not require the user to provide a
        # folder. Search the computer when no location is given, and accept
        # arbitrary drive references such as "D drive".
        drive_location = r"[A-Za-z]:(?:\s*drive)?|[A-Za-z]\s+drive|drive\s*[A-Za-z]"
        open_file_pattern = rf"^(?:open|launch|start|kholo)\s+(?:the\s+)?(?P<query>.+?)(?:\s+file)?(?:\s+from\s+(?:the\s+)?(?P<drive>{drive_location})|\s+in\s+(?:the\s+)?(?P<folder>desktop|downloads?|documents?|pictures?|computer|pc))?\s*$"
        open_match = re.match(open_file_pattern, compact, re.IGNORECASE)
        if open_match and not re.search(r"\b(?:app|application|website|browser)\b", compact, re.IGNORECASE):
            query = open_match.group("query").strip()
            if query and (re.search(r"\.[A-Za-z0-9]{1,8}$", query) or re.search(r"\b(?:file|folder|document|pdf|txt|image|photo|picture)\b", compact, re.IGNORECASE)):
                location = open_match.group("drive") or open_match.group("folder") or "computer"
                if open_match.group("drive"):
                    d = re.search(r"[A-Za-z]", open_match.group("drive"))
                    location = f"{d.group(0).upper()}:" if d else "computer"
                return {
                    "tool": "find_item",
                    "args": {
                        "query": query,
                        "location": location,
                        "item_type": "file",
                        "open_result": True,
                    },
                }

        # EXTENSION + LOCATION FILE COMMANDS
        # Handle commands such as:
        #   open .txt files from destop
        #   open all .txt files in desktop
        #   find .pdf files in Downloads
        #   search txt files from D drive
        # These must NOT fall through to fuzzy find_item(), because that can
        # return an unrelated filename (for example a .php file).
        extension_location = (
            r"my computer|this pc|downloads?|documents?|pictures?|desktop|"
            r"destop|computer|pc|[A-Za-z]:(?:\s*drive)?|[A-Za-z]\s+drive|drive\s*[A-Za-z]"
        )
        extension_command = re.match(
            rf"^(?P<action>open|launch|show|display|find|search|locate)\s+"
            rf"(?P<all>all\s+)?(?:the\s+)?(?P<extension>\.?[A-Za-z0-9]{1,8})\s+"
            rf"(?:files?|documents?)\s+(?:from|in|on|inside|under)\s+(?:the\s+)?"
            rf"(?P<location>{extension_location})\s*$",
            compact,
            re.IGNORECASE,
        )
        if extension_command:
            ext = extension_command.group("extension").strip()
            if not ext.startswith("."):
                ext = "." + ext

            location = extension_command.group("location").strip()
            location_aliases = {
                "destop": "desktop",
                "desktop": "desktop",
                "download": "downloads",
                "downloads": "downloads",
                "document": "documents",
                "documents": "documents",
                "picture": "pictures",
                "pictures": "pictures",
                "computer": "computer",
                "pc": "computer",
                "my pc": "computer",
                "my computer": "computer",
                "this pc": "computer",
            }
            location = location_aliases.get(location.lower(), location)
            if re.fullmatch(r"[A-Za-z]:?(?:\s*drive)?", location, re.IGNORECASE) or re.fullmatch(r"drive\s*[A-Za-z]", location, re.IGNORECASE):
                location = self._normalize_command_location(location)

            action = extension_command.group("action").lower()
            return {
                "tool": "find_by_extension",
                "args": {
                    "extension": ext,
                    "location": location,
                    "open_results": action in {"open", "launch"},
                },
            }

        # Natural file-search commands are deterministic so the user does not
        # need to know the exact filename or a single fixed sentence pattern.
        # Examples: "find amshal cv in pc", "amshal cv find in pc",
        # "search my resume on computer", "locate report in desktop".
        search_locations = r"my computer|this pc|downloads?|documents?|pictures?|desktop|computer|pc|[A-Za-z]:(?:\s*drive)?|[A-Za-z]\s+drive|drive\s*[A-Za-z]"
        search_words = r"find|search|look for|lookup|locate|look up|show me|show|get|dhundo|dhoondo|talash karo|search karo|find karo"

        # Latest/newest image queries are deterministic. "image" is a file
        # category, not a literal filename, so route it to the latest-file
        # tool with all common image extensions. This works for Downloads,
        # Pictures, Desktop, Documents, or Computer.
        image_extensions = ".jpg,.jpeg,.png,.gif,.bmp,.webp,.tif,.tiff,.heic,.heif,.jfif"
        latest_words = r"latest|newest|new|most recent|recent"
        image_words = r"image|images|photo|photos|picture|pictures|pic|pics"
        latest_location = r"my computer|this pc|downloads?|documents?|pictures?|desktop|computer|pc"

        # Media-specific latest queries MUST be deterministic. Otherwise the
        # LLM can turn "newest picture" into a generic latest-file request
        # and accidentally return a newer video.
        latest_image_patterns = [
            rf"^(?:what(?:\'s| is)?|show(?: me)?|find|search|get)?\s*(?:the\s+)?(?:{latest_words})\s+(?:and\s+)?(?:new\s+)?(?:{image_words})\s+(?:files?\s+)?(?:in|on|inside|under)\s+(?:the\s+)?(?P<location>{latest_location})\s*$",
            rf"^(?:what(?:\'s| is)?|show(?: me)?|find|search|get)?\s*(?:the\s+)?(?:{image_words})\s+(?:that\s+is\s+)?(?:the\s+)?(?:{latest_words})\s+(?:files?\s+)?(?:in|on|inside|under)\s+(?:the\s+)?(?P<location>{latest_location})\s*$",
        ]
        m = None
        for pattern in latest_image_patterns:
            m = re.match(pattern, compact, re.IGNORECASE)
            if m:
                break
        if m:
            return {
                "tool": "find_latest_file",
                "args": {
                    "location": m.group("location").strip(),
                    "extension": image_extensions,
                },
            }

        # Compound search + open: "search Postman-api file and open that".
        # Handle this before normal search parsing so the action words are not
        # accidentally treated as part of the filename query.
        m = re.match(
            rf"^(?:{search_words})\s+(?:for\s+)?(?P<query>.+?)(?:\s+file)?\s+and\s+open\s+(?:that|it)\s*$",
            compact,
            re.IGNORECASE,
        )
        if m:
            return {
                "tool": "find_item",
                "args": {
                    "query": m.group("query").strip(),
                    "location": "computer",
                    "item_type": "file",
                    "open_result": True,
                },
            }

        # Search verb first: extract everything between the verb and location.
        m = re.match(
            rf"^(?:{search_words})\s+(?:for\s+)?(?P<query>.+?)\s+(?:in|on|inside|under)\s+(?:the\s+)?(?P<location>{search_locations})\s*$",
            compact,
            re.IGNORECASE,
        )
        if m:
            return {
                "tool": "find_item",
                "args": {
                    "query": m.group("query").strip(),
                    "location": self._normalize_command_location(m.group("location")),
                    "item_type": None,
                },
            }

        # Location can appear first or the word "find" can appear at the end.
        m = re.match(
            rf"^(?P<query>.+?)\s+(?:{search_words})\s+(?:in|on|inside|under)\s+(?:the\s+)?(?P<location>{search_locations})\s*$",
            compact,
            re.IGNORECASE,
        )
        if m:
            return {
                "tool": "find_item",
                "args": {
                    "query": m.group("query").strip(),
                    "location": self._normalize_command_location(m.group("location")),
                    "item_type": None,
                },
            }

        m = re.match(
            rf"^(?P<query>.+?)\s+(?:{search_words})\s+(?:in|on|inside|under)\s+(?:the\s+)?(?P<location>{search_locations})\s*$",
            compact,
            re.IGNORECASE,
        )
        if m:
            return {
                "tool": "find_item",
                "args": {
                    "query": m.group("query").strip(),
                    "location": self._normalize_command_location(m.group("location")),
                    "item_type": None,
                },
            }

        # Common "find X" / "search X" without an explicit location -> computer.
        m = re.match(
            rf"^(?:{search_words})\s+(?:for\s+)?(?P<query>.+?)\s*$",
            compact,
            re.IGNORECASE,
        )
        if m and m.group("query").strip():
            query = m.group("query").strip()
            if not re.match(r"^(?:in|on|inside|under)\s+", query, re.IGNORECASE):
                return {
                    "tool": "find_item",
                    "args": {"query": query, "location": "computer", "item_type": None},
                }

        # WAMP status questions should inspect the actual process state.
        if (re.search(r"\b(?:wamp|wampp|wampserver|wamp server)\b", compact)
                and re.search(r"\b(?:running|open|opened|on|active|status|not open|isn't open|isnt open|why)\b", compact)):
            return {"tool": "check_app_status", "args": {"app_name": "WAMP"}}

        return plan

    
    # PLAN COMMAND
    

    def _deterministic_plan(self, command):
        """Resolve common desktop intents without depending on the LLM."""
        return self._repair_common_intent(command, {"tool": "unknown", "args": {}})

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

        # Resolve common Windows commands before Groq. This makes basic
        # natural-language automation reliable even if the AI planner is
        # unavailable or returns an imperfect tool.
        deterministic = self._deterministic_plan(command)
        if deterministic.get("tool") != "unknown":
            return self._validate_plan(deterministic)

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

        
        # GET CONTENT

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

        
        # PARSE JSON
        

        try:

            plan = json.loads(
                content
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "Planner returned invalid JSON:\n"
                f"{content}"
            ) from error

        
        # VALIDATE PLAN
        
        plan = self._repair_common_intent(command, plan)

        return self._validate_plan(
            plan
        )

    
    # VALIDATE PLANNER OUTPUT

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