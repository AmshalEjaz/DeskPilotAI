import json
import urllib.request
import urllib.error


class PlannerAgent:

    def __init__(
        self,
        model="qwen2.5:3b-instruct",
        ollama_url="http://localhost:11434/api/chat"
    ):

        self.model = model
        self.ollama_url = ollama_url

    # =========================================================
    # SYSTEM PROMPT
    # =========================================================

    def get_system_prompt(self):

        return """
You are the planning engine for DeskPilot AI,
a Windows desktop automation agent.

Your job is ONLY to understand the user's instruction
and convert it into ONE structured JSON tool call.

The user may speak:
- English
- Urdu
- Roman Urdu
- mixed English/Urdu
- informal language

Do not execute anything yourself.

Return JSON only.

Available tools:

1. open_file_explorer
Args:
{}

2. open_this_pc
Args:
{}

3. open_folder
Args:
{
    "location": "desktop|downloads|documents|pictures"
}

4. open_item
Args:
{
    "item_name": "name",
    "location": "desktop|downloads|documents|pictures"
}

5. list_files
Args:
{
    "location": "desktop|downloads|documents|pictures"
}

6. find_item
Args:
{
    "query": "text",
    "location": "desktop|downloads|documents|pictures",
    "item_type": "file|folder|null"
}

7. find_by_extension
Args:
{
    "extension": ".pdf",
    "location": "desktop|downloads|documents|pictures"
}

8. find_latest_file
Args:
{
    "location": "desktop|downloads|documents|pictures",
    "extension": ".pdf|null"
}

9. create_folder
Args:
{
    "folder_name": "name",
    "location": "desktop|downloads|documents|pictures"
}

10. create_file
Args:
{
    "file_name": "name",
    "location": "desktop|downloads|documents|pictures"
}

11. rename_item
Args:
{
    "old_name": "old name",
    "new_name": "new name",
    "location": "desktop|downloads|documents|pictures"
}

12. copy_item
Args:
{
    "item_name": "name",
    "source_location": "desktop|downloads|documents|pictures",
    "destination_location": "desktop|downloads|documents|pictures"
}

13. move_item
Args:
{
    "item_name": "name",
    "source_location": "desktop|downloads|documents|pictures",
    "destination_location": "desktop|downloads|documents|pictures"
}

14. browser_open
Args:
{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo"
}

15. browser_search
Args:
{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo",
    "query": "search text"
}

16. browser_close
Args:
{
    "site": "google|youtube|github|bing|wikipedia|duckduckgo"
}

17. unknown
Args:
{
    "reason": "short explanation"
}

Important rules:

- Never invent a tool.
- Never invent missing important information.
- Return only one tool call.
- Do not return markdown.
- Do not explain the answer.
- Do not use code fences.
- JSON must contain exactly:
  {
      "tool": "...",
      "args": {...}
  }

Interpret natural language intelligently.

Examples:

User:
open file explorer

Output:
{
    "tool": "open_file_explorer",
    "args": {}
}

User:
This PC kholo

Output:
{
    "tool": "open_this_pc",
    "args": {}
}

User:
desktop me MyDeskPilotTest folder dhundo

Output:
{
    "tool": "find_item",
    "args": {
        "query": "MyDeskPilotTest",
        "location": "desktop",
        "item_type": "folder"
    }
}

User:
downloads me latest pdf dhundo

Output:
{
    "tool": "find_latest_file",
    "args": {
        "location": "downloads",
        "extension": ".pdf"
    }
}

User:
youtube kholo

Output:
{
    "tool": "browser_open",
    "args": {
        "site": "youtube"
    }
}

User:
youtube par laravel beginners search kro

Output:
{
    "tool": "browser_search",
    "args": {
        "site": "youtube",
        "query": "laravel beginners"
    }
}
"""

    # =========================================================
    # CALL OLLAMA
    # =========================================================

    def plan(
        self,
        command
    ):

        command = command.strip()

        if not command:

            raise ValueError(
                "Command cannot be empty."
            )

        payload = {
            "model": self.model,

            "messages": [
                {
                    "role": "system",
                    "content": self.get_system_prompt()
                },
                {
                    "role": "user",
                    "content": command
                }
            ],

            "stream": False,

            "format": "json",

            "options": {
                "temperature": 0.1,
                "top_p": 0.2
            }
        }

        request_data = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        request = urllib.request.Request(
            self.ollama_url,
            data=request_data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=60
            ) as response:

                response_data = json.loads(
                    response
                    .read()
                    .decode("utf-8")
                )

        except urllib.error.URLError as error:

            raise RuntimeError(
                "Could not connect to Ollama. "
                "Make sure Ollama is running."
            ) from error

        # =====================================================
        # GET MODEL OUTPUT
        # =====================================================

        message = response_data.get(
            "message",
            {}
        )

        content = message.get(
            "content",
            ""
        ).strip()

        if not content:

            raise RuntimeError(
                "Planner returned an empty response."
            )

        # =====================================================
        # PARSE JSON
        # =====================================================

        try:

            plan = json.loads(
                content
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                f"Planner returned invalid JSON: {content}"
            ) from error

        # =====================================================
        # BASIC VALIDATION
        # =====================================================

        if not isinstance(
            plan,
            dict
        ):

            raise RuntimeError(
                "Planner response must be a JSON object."
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
                "Planner response is missing a valid tool."
            )

        if not isinstance(
            args,
            dict
        ):

            raise RuntimeError(
                "Planner response is missing valid args."
            )

        return plan