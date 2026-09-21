import os
import re
import json
import shutil
import subprocess
from pathlib import Path


class AppAgent:

    # =========================================================
    # COMMON USER ALIASES
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
    }

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self):

        self._apps_cache = None

    # =========================================================
    # NORMALIZE TEXT
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
    # NORMALIZE APP NAME / ALIAS
    # =========================================================

    def normalize_app_name(
        self,
        app_name
    ):

        app_name = self._normalize(
            app_name
        )

        if not app_name:

            raise ValueError(
                "App name cannot be empty."
            )

        return self.APP_ALIASES.get(
            app_name,
            app_name
        )

    # =========================================================
    # GET WINDOWS START MENU APPS
    # =========================================================

    def _load_start_apps(
        self,
        refresh=False
    ):

        if (
            self._apps_cache is not None
            and not refresh
        ):

            return self._apps_cache

        powershell_command = (
            "[Console]::OutputEncoding="
            "[System.Text.Encoding]::UTF8; "
            "Get-StartApps | "
            "Select-Object Name,AppID | "
            "ConvertTo-Json -Compress"
        )

        creation_flags = getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        )

        try:

            process = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    powershell_command,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                creationflags=creation_flags,
            )

        except (
            subprocess.SubprocessError,
            OSError
        ) as error:

            raise RuntimeError(
                "Could not read installed Windows apps."
            ) from error

        if process.returncode != 0:

            raise RuntimeError(
                "Windows could not return the "
                "installed app list."
            )

        output = (
            process.stdout
            .strip()
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
                "Windows returned an invalid "
                "installed-app response."
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

        query = self.normalize_app_name(
            query
        )

        apps = self._load_start_apps()

        matches = []

        for app in apps:

            normalized_name = self._normalize(
                app["name"]
            )

            if query in normalized_name:

                matches.append(
                    app
                )

            if len(matches) >= limit:
                break

        return matches

    # =========================================================
    # FIND EXACT / BEST WINDOWS APP
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
        # EXACT NORMALIZED MATCH
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

        starts_with = []

        for app in apps:

            current = self._normalize(
                app["name"]
            )

            if current.startswith(
                wanted
            ):

                starts_with.append(
                    app
                )

        if len(starts_with) == 1:

            return starts_with[0]

        # -----------------------------------------------------
        # CONTAINS MATCH
        # -----------------------------------------------------

        contains = []

        for app in apps:

            current = self._normalize(
                app["name"]
            )

            if wanted in current:

                contains.append(
                    app
                )

        if len(contains) == 1:

            return contains[0]

        return None

    # =========================================================
    # TRY KNOWN EXECUTABLE
    # =========================================================

    def _open_known_executable(
        self,
        app_name
    ):

        candidates = self.KNOWN_EXECUTABLES.get(
            app_name
        )

        if not candidates:

            return False

        for executable in candidates:

            resolved = shutil.which(
                executable
            )

            if not resolved:
                continue

            try:

                subprocess.Popen(
                    [
                        resolved
                    ]
                )

                return True

            except OSError:
                continue

        return False

    # =========================================================
    # FIND START MENU SHORTCUT
    # =========================================================

    def _find_start_menu_shortcut(
        self,
        app_name
    ):

        start_menu_locations = []

        appdata = os.environ.get(
            "APPDATA"
        )

        programdata = os.environ.get(
            "PROGRAMDATA"
        )

        if appdata:

            start_menu_locations.append(
                Path(appdata)
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
            )

        if programdata:

            start_menu_locations.append(
                Path(programdata)
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
            )

        # -----------------------------------------------------
        # EXACT MATCH FIRST
        # -----------------------------------------------------

        possible_matches = []

        for start_menu in start_menu_locations:

            if not start_menu.exists():
                continue

            try:

                for shortcut in start_menu.rglob(
                    "*.lnk"
                ):

                    normalized_name = self._normalize(
                        shortcut.stem
                    )

                    if normalized_name == app_name:

                        return shortcut

                    if app_name in normalized_name:

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
    # OPEN APP
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
        # SPECIAL WINDOWS SETTINGS
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
        # WINDOWS START APPS / MICROSOFT STORE APPS
        # =====================================================

        installed_app = self.find_app(
            normalized_name
        )

        if installed_app is not None:

            app_id = installed_app[
                "app_id"
            ]

            display_name = installed_app[
                "name"
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

        if shortcut is not None:

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
                f"Could not find an exact app named "
                f"'{requested_name}'. "
                f"Possible matches: {names}"
            )

        raise FileNotFoundError(
            f"App '{requested_name}' "
            f"was not found on this computer."
        )