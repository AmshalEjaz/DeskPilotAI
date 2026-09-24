import os
import re
import shutil
import subprocess
from pathlib import Path


class LocalSystemAgent:
    """Local-only diagnostics for DeskPilot.

    This agent intentionally does not use web/network search. It inspects
    Windows processes, services/ports, executables, disk space and common
    development tools available on the user's own PC.
    """

    def __init__(self):
        self.home = Path.home()

    def _run(self, args, timeout=8):
        try:
            p = subprocess.run(
                args, capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace"
            )
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except Exception as exc:
            return -1, str(exc)

    def _powershell(self, command, timeout=8):
        return self._run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            timeout=timeout,
        )

    def _processes(self):
        code, out = self._run(["tasklist", "/FO", "CSV", "/NH"])
        names = []
        if code == 0:
            for line in out.splitlines():
                m = re.match(r'"([^"]+)"', line.strip())
                if m:
                    names.append(m.group(1))
        return names

    def _port_owner(self, port):
        code, out = self._run(["netstat", "-ano", "-p", "tcp"])
        matches = []
        if code == 0:
            for line in out.splitlines():
                if f":{port}" in line and ("LISTENING" in line.upper()):
                    parts = line.split()
                    if len(parts) >= 5:
                        matches.append({"line": line.strip(), "pid": parts[-1]})
        return matches

    def _which(self, name):
        return shutil.which(name)

    def diagnose(self, query=""):
        q = str(query or "").strip().lower()
        data = {"query": query, "checks": {}}
        messages = []

        # Basic machine facts
        try:
            usage = shutil.disk_usage(self.home.anchor or self.home)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            data["checks"]["disk"] = {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
            }
            if free_gb < 5:
                messages.append(f"Disk space is low: only {free_gb:.1f} GB free.")
        except Exception:
            pass

        processes = self._processes()
        lower_processes = {p.lower() for p in processes}
        data["checks"]["process_count"] = len(processes)

        # Common developer/system executables
        executables = {}
        for name in ("python", "python3", "php", "mysql", "httpd", "node", "npm"):
            path = self._which(name)
            executables[name] = path
        data["checks"]["executables"] = executables

        # WAMP / Apache / MySQL
        wamp_processes = [p for p in processes if any(x in p.lower() for x in ("wamp", "wampmanager", "httpd.exe", "mysqld.exe"))]
        data["checks"]["wamp_processes"] = wamp_processes
        data["checks"]["ports"] = {
            "80": self._port_owner(80),
            "443": self._port_owner(443),
            "3306": self._port_owner(3306),
        }

        if "wamp" in q or "apache" in q or "mysql" in q or "xampp" in q:
            apache_running = any(p.lower() == "httpd.exe" for p in processes)
            mysql_running = any(p.lower() == "mysqld.exe" for p in processes)
            port80 = data["checks"]["ports"]["80"]
            port3306 = data["checks"]["ports"]["3306"]

            if apache_running:
                messages.append("Apache (httpd.exe) is currently running.")
            else:
                messages.append("Apache (httpd.exe) is not currently running.")

            if mysql_running:
                messages.append("MySQL (mysqld.exe) is currently running.")
            else:
                messages.append("MySQL (mysqld.exe) is not currently running.")

            if port80:
                pids = ", ".join(x["pid"] for x in port80)
                messages.append(f"Port 80 is occupied by PID {pids}.")
                if not apache_running:
                    messages.append("That can prevent Apache from starting on port 80.")
            else:
                messages.append("Port 80 has no detected TCP listener.")

            if port3306:
                messages.append("Port 3306 has a TCP listener.")
            else:
                messages.append("Port 3306 has no detected TCP listener.")

        # Python
        if "python" in q or "pip" in q or "py " in q:
            py = self._which("python")
            if py:
                code, out = self._run(["python", "--version"])
                version = out.strip()
                messages.append(f"Python is installed at {py}. {version}")
            else:
                messages.append("Python was not found on PATH.")

        # Chrome/browser
        if "chrome" in q or "browser" in q or "youtube" in q:
            chrome_names = [p for p in processes if "chrome.exe" in p.lower()]
            data["checks"]["chrome_processes"] = len(chrome_names)
            if chrome_names:
                messages.append(f"Chrome has {len(chrome_names)} running process(es).")
            else:
                messages.append("No Chrome process is currently running.")

        # Disk/storage
        if any(word in q for word in ("disk", "storage", "space", "drive")):
            d = data["checks"].get("disk")
            if d:
                messages.append(f"System drive: {d['free_gb']:.1f} GB free of {d['total_gb']:.1f} GB.")

        # Generic fallback: give useful local snapshot rather than claiming an
        # unsupported diagnosis.
        if not messages:
            messages.append(
                "I checked the local PC only. "
                f"Detected {len(processes)} running processes."
            )
            d = data["checks"].get("disk")
            if d:
                messages.append(f"{d['free_gb']:.1f} GB free on the system drive.")
            if executables.get("python"):
                messages.append("Python is available on PATH.")
            else:
                messages.append("Python is not available on PATH.")

        return {
            "message": "\n".join(messages),
            "data": data,
        }
