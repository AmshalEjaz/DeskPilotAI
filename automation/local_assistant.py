import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


class LocalAssistant:
    """DeskPilot's local/system-aware conversation and diagnosis layer.

    It never performs web searches. It gathers a small, relevant snapshot of
    the Windows machine and asks the configured language model to explain it.
    """

    def __init__(self, app_agent=None, file_agent=None, model=None):
        self.app_agent = app_agent
        self.file_agent = file_agent

        project_root = Path(__file__).resolve().parent.parent
        load_dotenv(project_root / ".env")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY was not found. Add it to the project .env file.")

        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = Groq(api_key=api_key, timeout=25.0, max_retries=0)

    def _powershell(self, command, timeout=8):
        if os.name != "nt":
            return "Windows-only diagnostic command was skipped."
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return (result.stdout or result.stderr).strip()
        except Exception as exc:
            return f"Diagnostic command failed: {exc}"

    def _safe_app_status(self, app_name):
        if not self.app_agent:
            return None
        try:
            return self.app_agent.check_app_status(app_name)
        except Exception as exc:
            return {"error": str(exc)}

    def _port_snapshot(self, ports):
        if os.name != "nt":
            return {}
        query = ",".join(str(p) for p in ports)
        command = (
            "$ports=@(" + query + "); "
            "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
            "Where-Object {$ports -contains $_.LocalPort} | "
            "Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"
        )
        raw = self._powershell(command)
        try:
            data = json.loads(raw) if raw else []
            return {"listeners": data if isinstance(data, list) else [data]}
        except Exception:
            return {"raw": raw}

    def _process_snapshot(self, patterns):
        if os.name != "nt":
            return []
        safe = [p.replace("'", "''") for p in patterns]
        pattern_expr = " -or ".join([f"$_.ProcessName -like '*{p}*'" for p in safe])
        command = (
            "Get-Process -ErrorAction SilentlyContinue | "
            f"Where-Object {{{pattern_expr}}} | "
            "Select-Object ProcessName,Id,Path | ConvertTo-Json -Compress"
        )
        raw = self._powershell(command)
        try:
            data = json.loads(raw) if raw else []
            return data if isinstance(data, list) else [data]
        except Exception:
            return [{"raw": raw}] if raw else []

    def collect_context(self, question):
        q = str(question or "").lower()
        context = {
            "machine": {
                "os": platform.platform(),
                "python": platform.python_version(),
                "computer_name": os.environ.get("COMPUTERNAME", "unknown"),
            },
            "deskpilot": {
                "working_directory": str(Path.cwd()),
            },
        }

        # Keep diagnostics targeted rather than dumping the whole machine.
        if any(x in q for x in ("wamp", "apache", "mysql", "xampp")):
            context["wamp"] = self._safe_app_status("WAMP")
            context["processes"] = self._process_snapshot(["wamp", "httpd", "mysqld", "apache"])
            context["ports"] = self._port_snapshot([80, 443, 3306, 8080])

        if any(x in q for x in ("python", "pip", "venv", "virtualenv")):
            context["python"] = {
                "executable": shutil.which("python") or shutil.which("python3"),
                "pip": shutil.which("pip") or shutil.which("pip3"),
                "version_output": self._powershell("python --version"),
            }

        if any(x in q for x in ("chrome", "browser", "youtube", "google")):
            context["browser_processes"] = self._process_snapshot(["chrome", "msedge", "firefox"])

        if any(x in q for x in ("disk", "storage", "space", "drive")):
            disks = {}
            if os.name == "nt":
                for drive in ("C:\\", "D:\\", "E:\\"):
                    try:
                        total, used, free = shutil.disk_usage(drive)
                        disks[drive] = {"total": total, "used": used, "free": free}
                    except OSError:
                        pass
            context["disks"] = disks

        # The assistant should not receive secrets or the contents of .env.
        context["rules"] = [
            "No web search is available in this assistant layer.",
            "Use only the supplied local/system context.",
            "Do not invent a diagnosis when the local evidence is insufficient.",
        ]
        return context

    def answer(self, question):
        question = str(question or "").strip()
        if not question:
            raise ValueError("Question cannot be empty.")

        context = self.collect_context(question)
        system_prompt = """
You are DeskPilot AI's local desktop assistant.

Your job is to answer the user's question using ONLY the supplied local
Windows/system context. You do NOT have web browsing in this mode.

DeskPilot is intended to understand and help with the user's own computer,
not act as a general internet search assistant.

Rules:
- Be conversational and useful.
- For troubleshooting, distinguish facts found in the context from likely causes.
- Never claim you checked something that is not present in the context.
- If evidence is insufficient, say exactly what local information is missing.
- Give practical next steps, but do not run or invent shell/PowerShell commands.
- Do not expose API keys, .env contents, tokens, passwords, or other secrets.
- If the user asks a generic question unrelated to their computer/project, explain
  that DeskPilot is focused on their local system and ask for the system/project context.
- Keep answers concise unless the user asks for detail.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Local context:\n"
                        + json.dumps(context, indent=2, default=str)
                        + "\n\nUser question:\n"
                        + question
                    ),
                },
            ],
            temperature=0.2,
        )

        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("The local assistant returned an empty response.")
        return response.choices[0].message.content.strip(), context
