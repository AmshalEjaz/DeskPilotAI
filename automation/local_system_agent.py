import os
import re
import shutil
import subprocess
import datetime
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



    # ------------------------------------------------------------
    # WINDOWS / WINDOW MANAGEMENT
    # ------------------------------------------------------------

    def _enum_windows(self):
        """Return visible top-level Windows windows with non-empty titles."""
        if os.name != "nt":
            return []
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        windows = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if not title or user32.GetParent(hwnd):
                return True
            windows.append({"hwnd": int(hwnd), "title": title})
            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)
        return windows

    def list_open_windows(self):
        windows = self._enum_windows()
        return {
            "count": len(windows),
            "windows": windows,
            "message": "\n".join(
                f"{i}. {item['title']}" for i, item in enumerate(windows, 1)
            ) if windows else "No visible application windows were found.",
        }

    def _find_window(self, target):
        target = str(target or "").strip().lower()
        if not target:
            return None
        windows = self._enum_windows()
        for item in windows:
            if item["title"].lower() == target:
                return item
        for item in windows:
            if target in item["title"].lower():
                return item
        return None

    def control_window(self, target, action="activate"):
        if os.name != "nt":
            raise RuntimeError("Window controls are available on Windows only.")
        import ctypes
        user32 = ctypes.windll.user32
        action = str(action or "activate").strip().lower()
        if action == "minimize_all":
            for item in self._enum_windows():
                user32.ShowWindow(item["hwnd"], 6)
            return "All visible windows were minimized."
        if action == "restore_all":
            for item in self._enum_windows():
                user32.ShowWindow(item["hwnd"], 9)
            return "All visible windows were restored."
        item = self._find_window(target)
        if not item:
            raise ValueError(f"I could not find an open window for '{target}'.")
        hwnd = item["hwnd"]
        actions = {"minimize": 6, "maximize": 3, "restore": 9}
        if action in actions:
            user32.ShowWindow(hwnd, actions[action])
            return f"{item['title']} {action}d successfully."
        if action in {"activate", "switch", "focus"}:
            user32.ShowWindow(hwnd, 9)
            user32.SetForegroundWindow(hwnd)
            return f"Switched to {item['title']}."
        raise ValueError(f"Unknown window action: {action}")

    def take_screenshot(self):
        """Capture the entire Windows virtual desktop, not the DeskPilot window."""
        if os.name != "nt":
            raise RuntimeError("Screenshots are available on Windows only.")

        import ctypes
        from ctypes import wintypes

        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output = desktop / f"DeskPilot_Screenshot_{stamp}.png"

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        # SM_XVIRTUALSCREEN=76, SM_YVIRTUALSCREEN=77,
        # SM_CXVIRTUALSCREEN=78, SM_CYVIRTUALSCREEN=79
        left = user32.GetSystemMetrics(76)
        top = user32.GetSystemMetrics(77)
        width = user32.GetSystemMetrics(78)
        height = user32.GetSystemMetrics(79)
        if width <= 0 or height <= 0:
            raise RuntimeError("Windows returned an invalid desktop size.")

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        SRCCOPY = 0x00CC0020
        BI_RGB = 0
        DIB_RGB_COLORS = 0

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        old_bitmap = gdi32.SelectObject(hdc_mem, hbitmap)
        try:
            if not gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, left, top, SRCCOPY):
                raise RuntimeError("Windows could not capture the virtual desktop.")

            header = BITMAPINFOHEADER()
            header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            header.biWidth = width
            header.biHeight = -height  # top-down bitmap
            header.biPlanes = 1
            header.biBitCount = 32
            header.biCompression = BI_RGB
            info = BITMAPINFO()
            info.bmiHeader = header
            buffer = (ctypes.c_ubyte * (width * height * 4))()
            copied = gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buffer, ctypes.byref(info), DIB_RGB_COLORS)
            if copied != height:
                raise RuntimeError("Windows could not read the captured desktop image.")

            # Write the PNG directly so screenshot capture does not depend on Pillow.
            # The captured buffer is BGRA; PNG stores scanlines as RGBA here.
            import struct
            import zlib

            raw_bgra = bytes(buffer)
            raw = bytearray()
            row_bytes = width * 4
            for y in range(height):
                raw.append(0)  # PNG filter: None
                row = raw_bgra[y * row_bytes:(y + 1) * row_bytes]
                for x in range(0, row_bytes, 4):
                    b, g, r, a = row[x:x + 4]
                    raw.extend((r, g, b, 255))

            def _png_chunk(kind, data):
                crc = zlib.crc32(kind)
                crc = zlib.crc32(data, crc) & 0xffffffff
                return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

            png = bytearray(b"\x89PNG\r\n\x1a\n")
            png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
            png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(raw), 6)))
            png.extend(_png_chunk(b"IEND", b""))
            output.write_bytes(png)
        finally:
            gdi32.SelectObject(hdc_mem, old_bitmap)
            gdi32.DeleteObject(hbitmap)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)

        if not output.exists():
            raise RuntimeError("Screenshot file was not created.")
        return f"Full desktop screenshot saved to {output}"

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
