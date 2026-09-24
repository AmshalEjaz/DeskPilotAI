import json
import os
import re
import shutil
import subprocess
from pathlib import Path


class AppAgent:

    # =========================================================
    # USER-FRIENDLY APP ALIASES
    # =========================================================

    APP_ALIASES = {
        "insta": "instagram",
        "ig": "instagram",

        "calc": "calculator",

        "explorer": "file explorer",
        "files": "file explorer",

        "vscode": "visual studio code",
        "vs code": "visual studio code",

        "chrome": "google chrome",
        "edge": "microsoft edge",

        "whatsapp desktop": "whatsapp",

        "wampp": "wamp",
        "wampserver": "wamp",
        "wamp server": "wamp",
    }

    # =========================================================
    # COMMON EXECUTABLE APPS
    # =========================================================

    KNOWN_EXECUTABLES = {
        "notepad": [
            "notepad.exe",
        ],

        "calculator": [
            "calc.exe",
        ],

        "file explorer": [
            "explorer.exe",
        ],

        "command prompt": [
            "cmd.exe",
        ],

        "powershell": [
            "powershell.exe",
        ],

        "task manager": [
            "taskmgr.exe",
        ],

        "paint": [
            "mspaint.exe",
        ],

        "visual studio code": [
            "code.exe",
            "code",
        ],

        "google chrome": [
            "chrome.exe",
            "chrome",
        ],

        "microsoft edge": [
            "msedge.exe",
            "msedge",
        ],

        "wamp": [
            "wampmanager.exe",
            "wampmanager",
            r"C:\wamp64\wampmanager.exe",
            r"C:\wamp\wampmanager.exe",
        ],
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):

        self._apps_cache = None

        self.creation_flags = getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        )

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    def _normalize(
        self,
        value
    ):

        if value is None:
            return ""

        value = (
            str(value)
            .lower()
            .strip()
        )

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value.strip()

    # =========================================================
    # APP NAME NORMALIZATION
    # =========================================================

    def normalize_app_name(
        self,
        app_name
    ):

        normalized = self._normalize(
            app_name
        )

        if not normalized:

            raise ValueError(
                "App name cannot be empty."
            )

        return self.APP_ALIASES.get(
            normalized,
            normalized
        )

    # =========================================================
    # RUN POWERSHELL
    # =========================================================

    def _run_powershell(
        self,
        command,
        timeout=20
    ):

        try:

            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=self.creation_flags,
            )

        except subprocess.TimeoutExpired as error:

            raise RuntimeError(
                "Windows app lookup timed out."
            ) from error

        except OSError as error:

            raise RuntimeError(
                "Could not start Windows PowerShell."
            ) from error

        if result.returncode != 0:

            error_message = (
                result.stderr.strip()
                or
                "PowerShell command failed."
            )

            raise RuntimeError(
                error_message
            )

        return result.stdout.strip()

    # =========================================================
    # LOAD WINDOWS START APPS
    # =========================================================

    def _load_start_apps(
        self,
        refresh=False
    ):

        if (
            self._apps_cache is not None
            and
            not refresh
        ):

            return self._apps_cache

        command = (
            "[Console]::OutputEncoding="
            "[System.Text.Encoding]::UTF8; "
            "Get-StartApps | "
            "Select-Object Name,AppID | "
            "ConvertTo-Json -Compress"
        )

        output = self._run_powershell(
            command
        )

        if not output:

            self._apps_cache = []

            return []

        try:

            data = json.loads(
                output
            )

        except json.JSONDecodeError as error:

            raise RuntimeError(
                "Windows returned invalid "
                "installed-app information."
            ) from error

        if isinstance(
            data,
            dict
        ):

            data = [
                data
            ]

        if not isinstance(
            data,
            list
        ):

            data = []

        apps = []

        for item in data:

            if not isinstance(
                item,
                dict
            ):
                continue

            name = item.get(
                "Name"
            )

            app_id = item.get(
                "AppID"
            )

            if not name or not app_id:
                continue

            apps.append(
                {
                    "name": str(name),
                    "app_id": str(app_id),
                }
            )

        self._apps_cache = apps

        return apps

    # =========================================================
    # LIST INSTALLED APPS
    # =========================================================

    def list_apps(
        self,
        refresh=False
    ):

        apps = self._load_start_apps(
            refresh=refresh
        )

        return sorted(
            apps,
            key=lambda app: (
                app["name"].lower()
            )
        )

    # =========================================================
    # SEARCH INSTALLED APPS
    # =========================================================

    def search_apps(
        self,
        query,
        limit=20
    ):

        wanted = self.normalize_app_name(
            query
        )

        apps = self._load_start_apps()

        exact = []
        starts = []
        contains = []

        for app in apps:

            name = self._normalize(
                app["name"]
            )

            if name == wanted:

                exact.append(
                    app
                )

            elif name.startswith(
                wanted
            ):

                starts.append(
                    app
                )

            elif wanted in name:

                contains.append(
                    app
                )

        matches = (
            exact
            + starts
            + contains
        )

        return matches[:limit]

    # =========================================================
    # FIND BEST APP
    # =========================================================

    def find_app(
        self,
        app_name
    ):

        wanted = self.normalize_app_name(
            app_name
        )

        apps = self._load_start_apps()

        # -----------------------------------------------------
        # EXACT MATCH
        # -----------------------------------------------------

        for app in apps:

            current = self._normalize(
                app["name"]
            )

            if current == wanted:

                return app

        # -----------------------------------------------------
        # STARTS-WITH MATCH
        # -----------------------------------------------------

        matches = []

        for app in apps:

            current = self._normalize(
                app["name"]
            )

            if current.startswith(
                wanted
            ):

                matches.append(
                    app
                )

        if len(matches) == 1:

            return matches[0]

        # -----------------------------------------------------
        # CONTAINS MATCH
        # -----------------------------------------------------

        matches = []

        for app in apps:

            current = self._normalize(
                app["name"]
            )

            if wanted in current:

                matches.append(
                    app
                )

        if len(matches) == 1:

            return matches[0]

        return None

    # =========================================================
    # FIND KNOWN EXECUTABLE PATH
    # =========================================================

    def _find_known_executable(
        self,
        normalized_name
    ):

        candidates = self.KNOWN_EXECUTABLES.get(
            normalized_name
        )

        if not candidates:

            return None

        for executable in candidates:

            candidate_path = Path(executable)
            if candidate_path.is_file():
                return str(candidate_path.resolve())

            path = shutil.which(
                executable
            )

            if path:

                return str(
                    Path(path).resolve()
                )

        return None

    # =========================================================
    # START MENU LOCATIONS
    # =========================================================

    def _get_start_menu_locations(
        self
    ):

        locations = []

        appdata = os.environ.get(
            "APPDATA"
        )

        programdata = os.environ.get(
            "PROGRAMDATA"
        )

        if appdata:

            locations.append(
                Path(appdata)
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
            )

        if programdata:

            locations.append(
                Path(programdata)
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
            )

        return locations

    # =========================================================
    # FIND START MENU SHORTCUT
    # =========================================================

    def _find_start_menu_shortcut(
        self,
        app_name
    ):

        possible_matches = []

        for start_menu in (
            self._get_start_menu_locations()
        ):

            if not start_menu.exists():
                continue

            try:

                for shortcut in start_menu.rglob(
                    "*.lnk"
                ):

                    shortcut_name = (
                        self._normalize(
                            shortcut.stem
                        )
                    )

                    if shortcut_name == app_name:

                        return shortcut

                    if app_name in shortcut_name:

                        possible_matches.append(
                            shortcut
                        )

            except (
                PermissionError,
                OSError
            ):

                continue

        if len(possible_matches) == 1:

            return possible_matches[0]

        return None

    # =========================================================
    # RESOLVE WINDOWS SHORTCUT TARGET
    # =========================================================

    def _resolve_shortcut_target(
        self,
        shortcut
    ):

        shortcut_path = str(
            shortcut
        )

        safe_path = shortcut_path.replace(
            "'",
            "''"
        )

        command = (
            "$shell = New-Object -ComObject WScript.Shell; "
            f"$shortcut = $shell.CreateShortcut('{safe_path}'); "
            "[PSCustomObject]@{"
            "TargetPath=$shortcut.TargetPath;"
            "Arguments=$shortcut.Arguments;"
            "WorkingDirectory=$shortcut.WorkingDirectory"
            "} | ConvertTo-Json -Compress"
        )

        try:

            output = self._run_powershell(
                command
            )

        except Exception:

            return None

        if not output:

            return None

        try:

            result = json.loads(
                output
            )

        except json.JSONDecodeError:

            return None

        if not isinstance(
            result,
            dict
        ):

            return None

        return result

    # =========================================================
    # GET MICROSOFT STORE / APPX PACKAGE INFO
    # =========================================================

    def _get_appx_info(
        self,
        app_id
    ):

        if not app_id:
            return None

        # UWP / Store Start App IDs normally look like:
        #
        # PackageFamilyName!ApplicationId

        if "!" not in app_id:
            return None

        package_family = app_id.split(
            "!",
            1
        )[0]

        safe_family = package_family.replace(
            "'",
            "''"
        )

        command = (
            "[Console]::OutputEncoding="
            "[System.Text.Encoding]::UTF8; "
            "Get-AppxPackage | "
            "Where-Object { "
            f"$_.PackageFamilyName -eq '{safe_family}' "
            "} | "
            "Select-Object -First 1 "
            "Name,"
            "PackageFullName,"
            "PackageFamilyName,"
            "InstallLocation | "
            "ConvertTo-Json -Compress"
        )

        try:

            output = self._run_powershell(
                command
            )

        except Exception:

            return None

        if not output:

            return None

        try:

            result = json.loads(
                output
            )

        except json.JSONDecodeError:

            return None

        if not isinstance(
            result,
            dict
        ):

            return None

        return result

    # =========================================================
    # GET APP INFORMATION / LOCATION
    # =========================================================

    def get_app_info(
        self,
        app_name
    ):

        requested_name = str(
            app_name
        ).strip()

        if not requested_name:

            raise ValueError(
                "App name cannot be empty."
            )

        normalized_name = (
            self.normalize_app_name(
                requested_name
            )
        )

        result = {
            "found": False,
            "requested_name": requested_name,
            "name": None,
            "app_id": None,
            "app_type": None,
            "location": None,
            "executable_path": None,
            "shortcut_path": None,
            "package_name": None,
            "package_full_name": None,
            "package_family_name": None,
        }

        # =====================================================
        # KNOWN EXECUTABLE
        # =====================================================

        executable_path = (
            self._find_known_executable(
                normalized_name
            )
        )

        if executable_path:

            result.update(
                {
                    "found": True,
                    "name": requested_name,
                    "app_type": "desktop",
                    "location": str(
                        Path(
                            executable_path
                        ).parent
                    ),
                    "executable_path": (
                        executable_path
                    ),
                }
            )

        # =====================================================
        # START APPS
        # =====================================================

        installed_app = self.find_app(
            normalized_name
        )

        if installed_app:

            result["found"] = True
            result["name"] = installed_app[
                "name"
            ]

            result["app_id"] = installed_app[
                "app_id"
            ]

            # -------------------------------------------------
            # CHECK STORE / APPX PACKAGE
            # -------------------------------------------------

            appx_info = self._get_appx_info(
                installed_app[
                    "app_id"
                ]
            )

            if appx_info:

                install_location = (
                    appx_info.get(
                        "InstallLocation"
                    )
                )

                result.update(
                    {
                        "app_type":
                            "microsoft_store",

                        "location":
                            install_location,

                        "package_name":
                            appx_info.get(
                                "Name"
                            ),

                        "package_full_name":
                            appx_info.get(
                                "PackageFullName"
                            ),

                        "package_family_name":
                            appx_info.get(
                                "PackageFamilyName"
                            ),
                    }
                )

        # =====================================================
        # START MENU SHORTCUT
        # =====================================================

        shortcut = (
            self._find_start_menu_shortcut(
                normalized_name
            )
        )

        if shortcut:

            result["found"] = True

            result["shortcut_path"] = str(
                shortcut
            )

            shortcut_info = (
                self._resolve_shortcut_target(
                    shortcut
                )
            )

            if shortcut_info:

                target_path = (
                    shortcut_info.get(
                        "TargetPath"
                    )
                )

                if target_path:

                    result[
                        "executable_path"
                    ] = target_path

                    try:

                        result[
                            "location"
                        ] = str(
                            Path(
                                target_path
                            ).parent
                        )

                    except Exception:

                        pass

                if not result["app_type"]:

                    result[
                        "app_type"
                    ] = "desktop"

        # =====================================================
        # NOT FOUND
        # =====================================================

        if not result["found"]:

            suggestions = self.search_apps(
                normalized_name,
                limit=5
            )

            result["suggestions"] = [
                item["name"]
                for item in suggestions
            ]

        return result

    # =========================================================
    # FORMAT APP INFORMATION
    # =========================================================

    def format_app_info(
        self,
        info
    ):

        if not info.get(
            "found"
        ):

            requested = info.get(
                "requested_name",
                "application"
            )

            suggestions = info.get(
                "suggestions",
                []
            )

            if suggestions:

                return (
                    f"App '{requested}' was not "
                    f"found exactly.\n"
                    f"Possible matches: "
                    f"{', '.join(suggestions)}"
                )

            return (
                f"App '{requested}' "
                f"was not found on this computer."
            )

        lines = [
            (
                "App found: "
                f"{info.get('name')}"
            )
        ]

        app_type = info.get(
            "app_type"
        )

        if app_type:

            if app_type == "microsoft_store":

                lines.append(
                    "Type: Microsoft Store app"
                )

            else:

                lines.append(
                    "Type: Desktop application"
                )

        app_id = info.get(
            "app_id"
        )

        if app_id:

            lines.append(
                f"App ID: {app_id}"
            )

        executable_path = info.get(
            "executable_path"
        )

        if executable_path:

            lines.append(
                "Executable: "
                f"{executable_path}"
            )

        location = info.get(
            "location"
        )

        if location:

            lines.append(
                f"Location: {location}"
            )

        shortcut_path = info.get(
            "shortcut_path"
        )

        if shortcut_path:

            lines.append(
                "Start Menu shortcut: "
                f"{shortcut_path}"
            )

        package_full_name = info.get(
            "package_full_name"
        )

        if package_full_name:

            lines.append(
                "Package: "
                f"{package_full_name}"
            )

        if (
            not location
            and
            app_type == "microsoft_store"
        ):

            lines.append(
                "Physical installation location "
                "is managed by Windows."
            )

        return "\n".join(
            lines
        )

    # =========================================================
    # OPEN KNOWN EXECUTABLE
    # =========================================================

    def _open_known_executable(
        self,
        app_name
    ):

        path = self._find_known_executable(
            app_name
        )

        if not path:

            return False

        try:

            subprocess.Popen(
                [
                    path
                ]
            )

            return True

        except OSError:

            return False

    # =========================================================
    # OPEN INSTALLED APP
    # =========================================================

    def open_app(
        self,
        app_name
    ):

        requested_name = str(
            app_name
        ).strip()

        if not requested_name:

            raise ValueError(
                "App name cannot be empty."
            )

        normalized_name = (
            self.normalize_app_name(
                requested_name
            )
        )
    
        # =====================================================
        # WINDOWS SETTINGS
        # =====================================================

        if normalized_name in {
            "settings",
            "windows settings",
        }:

            os.startfile(
                "ms-settings:"
            )

            return (
                "Windows Settings opened successfully."
            )

        # =====================================================
        # KNOWN EXECUTABLE
        # =====================================================

        if self._open_known_executable(
            normalized_name
        ):

            return (
                f"{requested_name} "
                f"opened successfully."
            )

        # =====================================================
        # WINDOWS START APP
        # =====================================================

        installed_app = self.find_app(
            normalized_name
        )

        if installed_app:

            display_name = installed_app[
                "name"
            ]

            app_id = installed_app[
                "app_id"
            ]

            try:

                subprocess.Popen(
                    [
                        "explorer.exe",
                        (
                            "shell:AppsFolder\\"
                            + app_id
                        ),
                    ]
                )

            except OSError as error:

                raise RuntimeError(
                    f"Could not open "
                    f"{display_name}."
                ) from error

            return (
                f"{display_name} "
                f"opened successfully."
            )

        # =====================================================
        # START MENU SHORTCUT FALLBACK
        # =====================================================

        shortcut = (
            self._find_start_menu_shortcut(
                normalized_name
            )
        )

        if shortcut:

            try:

                os.startfile(
                    str(shortcut)
                )

            except OSError as error:

                raise RuntimeError(
                    f"Could not open "
                    f"{requested_name}."
                ) from error

            return (
                f"{requested_name} "
                f"opened successfully."
            )

        # =====================================================
        # NOT FOUND
        # =====================================================

        suggestions = self.search_apps(
            normalized_name,
            limit=5
        )

        if suggestions:

            names = ", ".join(
                app["name"]
                for app in suggestions
            )

            raise FileNotFoundError(
                f"Could not find an exact app "
                f"named '{requested_name}'. "
                f"Possible matches: {names}"
            )

        raise FileNotFoundError(
            f"App '{requested_name}' "
            f"was not found on this computer."
        )

    # =========================================================
    # RUNNING APP PROCESS ALIASES
    # =========================================================

    PROCESS_ALIASES = {
        "wps office": [
            "wps",
            "wpp",
            "et",
        ],

        "wps": [
            "wps",
            "wpp",
            "et",
        ],

        "instagram": [
            "instagram",
        ],

        "notepad": [
            "notepad",
        ],

        "calculator": [
            "calculatorapp",
            "calculator",
        ],

        "google chrome": [
            "chrome",
        ],

        "chrome": [
            "chrome",
        ],

        "microsoft edge": [
            "msedge",
        ],

        "edge": [
            "msedge",
        ],

        "wamp": [
            "wampmanager",
            "wamp64manager",
        ],

        "visual studio code": [
            "code",
        ],

        "vscode": [
            "code",
        ],
    }

    # =========================================================
    # GET RUNNING WINDOWED APPS
    # =========================================================

    def _get_running_apps(self):

        command = (
            "[Console]::OutputEncoding="
            "[System.Text.Encoding]::UTF8; "
            "Get-Process | "
            "Where-Object { $_.MainWindowHandle -ne 0 } | "
            "Select-Object Id,ProcessName,MainWindowTitle | "
            "ConvertTo-Json -Compress"
        )

        output = self._run_powershell(
            command,
            timeout=15
        )

        if not output:
            return []

        try:
            data = json.loads(output)

        except json.JSONDecodeError:
            return []

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            return []

        return data

    # =========================================================
    # CHECK WHETHER AN APP IS CURRENTLY RUNNING
    # =========================================================

    def check_app_status(
        self,
        app_name
    ):

        requested_name = str(app_name).strip()
        if not requested_name:
            raise ValueError("App name cannot be empty.")

        normalized_name = self.normalize_app_name(requested_name)
        running_apps = self._get_running_apps()
        aliases = self.PROCESS_ALIASES.get(normalized_name, [])
        matches = []

        for process in running_apps:
            process_name = self._normalize(process.get("ProcessName", ""))
            window_title = self._normalize(process.get("MainWindowTitle", ""))

            alias_match = any(
                self._normalize(alias) == process_name
                for alias in aliases
            )
            process_match = (
                normalized_name == process_name
                or normalized_name in process_name
                or process_name in normalized_name
            )
            title_match = bool(
                normalized_name and normalized_name in window_title
            )

            if alias_match or process_match or title_match:
                matches.append(process)

        installed = False
        try:
            installed = bool(self.get_app_info(requested_name).get("found"))
        except Exception:
            installed = False

        return {
            "requested_name": requested_name,
            "name": normalized_name,
            "running": bool(matches),
            "installed": installed,
            "process_names": sorted({
                str(item.get("ProcessName", ""))
                for item in matches
                if item.get("ProcessName")
            }),
            "processes": matches,
        }

    # =========================================================
    # CLOSE WINDOW BY TITLE / FILE / FOLDER NAME
    # =========================================================

    def close_window(self, target):
        """Close a visible file, folder, image, document, or other window.

        Explorer folder windows are handled through Shell.Application first;
        this closes the individual Explorer window instead of terminating
        explorer.exe. A Win32 WM_CLOSE fallback handles documents, images,
        PDFs, Notepad, Photos, and other visible windows by title.
        """
        requested = str(target or "").strip()
        if not requested:
            raise ValueError("Window, file, or folder name is required.")

        normalized = self._normalize(requested)
        if not normalized:
            raise ValueError("Window, file, or folder name is required.")

        escaped = requested.replace("'", "''")

        # 1) Explorer/Shell window: target the individual folder window.
        folder_script = fr"""
$target = '{escaped}'
$closed = 0
try {{
    $shell = New-Object -ComObject Shell.Application
    foreach ($w in @($shell.Windows())) {{
        try {{
            $loc = [string]$w.LocationName
            $full = ''
            try {{ $full = [string]$w.Document.Folder.Self.Path }} catch {{}}
            $href = [string]$w.FullName
            if ($href -match '(?i)explorer\.exe$') {{
                $hay = (($loc + ' ' + $full).ToLowerInvariant())
                if ($hay.Contains($target.ToLowerInvariant())) {{
                    $w.Quit()
                    $closed++
                }}
            }}
        }} catch {{}}
    }}
}} catch {{}}
$closed
"""
        try:
            output = self._run_powershell(folder_script, timeout=15)
            if output and output.strip().isdigit() and int(output.strip()) > 0:
                return f"'{requested}' closed successfully."
        except Exception:
            pass

        # 2) Generic top-level window close using Win32 WM_CLOSE.
        title_script = f"""
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class DeskPilotWin32 {{
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}}
'@
$target = '{escaped}'.ToLowerInvariant()
$WM_CLOSE = 0x0010
$closed = 0
[DeskPilotWin32]::EnumWindows({{
    param($hWnd, $lParam)
    if (-not [DeskPilotWin32]::IsWindowVisible($hWnd)) {{ return $true }}
    $sb = New-Object System.Text.StringBuilder 512
    [void][DeskPilotWin32]::GetWindowText($hWnd, $sb, $sb.Capacity)
    $title = $sb.ToString()
    if ([string]::IsNullOrWhiteSpace($title)) {{ return $true }}
    $lower = $title.ToLowerInvariant()
    if ($lower.Contains('deskpilot ai')) {{ return $true }}
    if ($lower.Contains($target)) {{
        if ([DeskPilotWin32]::PostMessage($hWnd, $WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero)) {{ $script:closed++ }}
    }}
    return $true
}}, [IntPtr]::Zero) | Out-Null
$closed
"""
        try:
            output = self._run_powershell(title_script, timeout=15)
            if output and output.strip().isdigit() and int(output.strip()) > 0:
                return f"'{requested}' closed successfully."
        except Exception:
            pass

        # 3) Last fallback for applications exposing a normal main window.
        windows = self._get_running_apps()
        matches = []
        for window in windows:
            title = str(window.get("MainWindowTitle") or "").strip()
            if title and normalized in self._normalize(title):
                matches.append(window)

        for window in matches:
            process_id = window.get("Id")
            if not process_id:
                continue
            command = (
                f"$p = Get-Process -Id {int(process_id)} "
                f"-ErrorAction SilentlyContinue; "
                "if ($p) { $p.CloseMainWindow() }"
            )
            try:
                self._run_powershell(command, timeout=10)
            except Exception:
                pass

        if matches:
            return f"'{requested}' close request sent successfully."

        raise RuntimeError(
            f"I could not find an open window for '{requested}'."
        )

    # =========================================================
    # CLOSE INSTALLED / DESKTOP APP
    # =========================================================

    def close_app(
        self,
        app_name
    ):

        requested_name = str(
            app_name
        ).strip()

        if not requested_name:

            raise ValueError(
                "App name cannot be empty."
            )

        normalized_name = (
            self.normalize_app_name(
                requested_name
            )
        )

        running_apps = (
            self._get_running_apps()
        )

        process_aliases = (
            self.PROCESS_ALIASES.get(
                normalized_name,
                []
            )
        )

        matches = []

        for process in running_apps:

            process_name = self._normalize(
                process.get(
                    "ProcessName",
                    ""
                )
            )

            window_title = self._normalize(
                process.get(
                    "MainWindowTitle",
                    ""
                )
            )

            # Known process alias
            alias_match = any(
                self._normalize(alias)
                == process_name
                for alias in process_aliases
            )

            # Generic process name match
            process_match = (
                normalized_name == process_name
                or
                normalized_name in process_name
                or
                process_name in normalized_name
            )

            # Window title match
            title_match = (
                normalized_name
                and
                normalized_name in window_title
            )

            if (
                alias_match
                or
                process_match
                or
                title_match
            ):

                matches.append(
                    process
                )

        if not matches:

            raise RuntimeError(
                f"{requested_name} does not appear "
                f"to be currently open."
            )

        closed_count = 0

        for process in matches:

            process_id = process.get(
                "Id"
            )

            if not process_id:
                continue

            command = (
                f"$p = Get-Process -Id {int(process_id)} "
                f"-ErrorAction SilentlyContinue; "
                "if ($p) { "
                "$result = $p.CloseMainWindow(); "
                "$result "
                "}"
            )

            try:

                output = self._run_powershell(
                    command,
                    timeout=10
                )

                if (
                    output
                    and
                    output.strip().lower()
                    == "true"
                ):
                    closed_count += 1

            except Exception:
                continue

        if closed_count == 0:

            raise RuntimeError(
                f"Could not send a close request "
                f"to {requested_name}."
            )

        return (
            f"{requested_name} close request sent successfully."
        )

