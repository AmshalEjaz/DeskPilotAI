import os
import shutil
import subprocess
import re
from difflib import SequenceMatcher

from pathlib import Path


class FileAgent:

    def __init__(self):

        self.home = Path.home()

        self.desktop = self._find_folder(
            "Desktop"
        )

        self.downloads = self._find_folder(
            "Downloads"
        )

        self.documents = self._find_folder(
            "Documents"
        )

        self.pictures = self._find_folder(
            "Pictures"
        )

        self.allowed_locations = {
            "desktop": self.desktop,
            "downloads": self.downloads,
            "documents": self.documents,
            "pictures": self.pictures,
        }

        # Searches labeled as "computer/PC" cover all available Windows
        # drive roots, not just Desktop/Downloads/Documents/Pictures.
        self.search_roots = self._build_search_roots()

    
    def _build_search_roots(self):
        roots = []

        # Include every available Windows drive (C:, D:, E:, ...).
        # This makes "find ... in computer" genuinely mean the PC.
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = Path(f"{letter}:\\")
            try:
                if drive.exists():
                    roots.append(drive)
            except OSError:
                continue

        unique = []
        seen = set()
        # Fallback for unusual Windows environments where drive-root probing
        # is unavailable.
        if not unique:
            for path in (self.pictures, self.desktop, self.downloads, self.documents):
                if path and path.exists():
                    key = str(path).casefold()
                    if key not in seen:
                        seen.add(key)
                        unique.append(path)
        return unique

    # FIND WINDOWS USER FOLDER
    

    def _find_folder(
        self,
        folder_name
    ):

        normal_path = (
            self.home
            / folder_name
        )

        if normal_path.exists():
            return normal_path

        # OneDrive redirected folders
        onedrive_path = (
            self.home
            / "OneDrive"
            / folder_name
        )

        if onedrive_path.exists():
            return onedrive_path

        return normal_path

    
    # NORMALIZE LOCATION
    

    def normalize_location(
        self,
        location
    ):

        if not location:

            raise ValueError(
                "Location is required."
            )

        location = (
            location
            .lower()
            .strip()
        )

        # Accept natural drive references such as "D drive", "D: drive",
        # "D:", or "drive D".
        drive_match = re.match(r"^(?:drive\s*)?([a-z])(?:\s*drive)?(?::)?$", location, re.IGNORECASE)
        if drive_match:
            return f"{drive_match.group(1).upper()}:"

        aliases = {

            "desktop": "desktop",

            "download": "downloads",
            "downloads": "downloads",

            "document": "documents",
            "documents": "documents",

            "picture": "pictures",
            "pictures": "pictures",
            "photo": "pictures",
            "photos": "pictures",
            "computer": "computer",
            "pc": "computer",
            "my pc": "computer",
            "my computer": "computer",
            "system": "computer",
        }

        return aliases.get(
            location,
            location
        )

    
    # RESOLVE LOCATION
    

    def get_location(
        self,
        location
    ):

        location = self.normalize_location(
            location
        )

        if location == "computer":
            return None

        if re.fullmatch(r"[A-Z]:", location):
            path = Path(f"{location}\\")
            if path.exists():
                return path
            raise ValueError(f"Drive {location} is not available.")

        path = self.allowed_locations.get(
            location
        )

        if path is None:

            supported = ", ".join(
                list(self.allowed_locations.keys()) + ["computer"]
            )

            raise ValueError(
                f"Unknown location '{location}'. "
                f"Supported locations: {supported}"
            )

        return path

    
    # SAFETY
    

    def _safe_child(
        self,
        base_folder,
        item_name
    ):

        base_folder = Path(
            base_folder
        ).resolve()

        target = (
            base_folder
            / item_name
        ).resolve()

        try:

            target.relative_to(
                base_folder
            )

        except ValueError:

            raise ValueError(
                "That path is outside the allowed folder."
            )

        return target

    
    # OPEN FILE EXPLORER
    

    def recycle_bin(self, action="open"):
        """Open and/or count items in the real Windows Recycle Bin."""
        if os.name != "nt":
            raise RuntimeError("Recycle Bin is only available on Windows.")

        action = str(action or "open").strip().lower()
        if action not in {"open", "count", "open_and_count", "empty", "close"}:
            raise ValueError("Unsupported Recycle Bin action.")

        if action == "empty":
            # Do not use PowerShell Clear-RecycleBin here: on some Windows
            # configurations it resolves the virtual RecycleBin: provider
            # incorrectly and raises "The system cannot find the path specified".
            # SHEmptyRecycleBinW is the native Windows API for this operation.
            import ctypes
            flags = 0x00000001 | 0x00000002 | 0x00000004  # no confirm/progress/sound
            rc = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            if rc != 0:
                raise RuntimeError(f"Could not empty Recycle Bin (Windows error {rc}).")
            return {"message": "Recycle Bin emptied successfully.", "files": 0, "folders": 0, "total": 0}

        if action == "close":
            # Recycle Bin is a virtual Explorer namespace. Do not depend on the
            # visible window title: Windows can localize/change that title.
            # Its Shell namespace URL has a stable Recycle Bin CLSID.
            ps = r'''
$closed = 0
$recycleUrl = "::{645FF040-5081-101B-9F08-00AA002F954E}"
try {
    $shell = New-Object -ComObject Shell.Application
    foreach ($w in @($shell.Windows())) {
        try {
            $full = [string]$w.FullName
            if ($full -notmatch '(?i)explorer\.exe$') { continue }

            $url = ''
            try { $url = [string]$w.LocationURL } catch {}
            $loc = ''
            try { $loc = [string]$w.LocationName } catch {}
            $path = ''
            try { $path = [string]$w.Document.Folder.Self.Path } catch {}
            $name = ''
            try { $name = [string]$w.Document.Folder.Self.Name } catch {}
            $parsing = ''
            try { $parsing = [string]$w.Document.Folder.Self.ParsingName } catch {}

            $isRecycleBin = ($url -match '(?i)645FF040-5081-101B-9F08-00AA002F954E|RecycleBinFolder') -or
                            ($loc -match '(?i)Recycle Bin') -or
                            ($path -match '(?i)645FF040-5081-101B-9F08-00AA002F954E|RecycleBinFolder') -or
                            ($name -match '(?i)Recycle Bin') -or
                            ($parsing -match '(?i)645FF040-5081-101B-9F08-00AA002F954E|RecycleBinFolder')

            if ($isRecycleBin) {
                $hwnd = 0
                try { $hwnd = [int64]$w.HWND } catch {}
                if ($hwnd -ne 0) {
                    try {
                        if (-not ('DeskPilotRecycleClose' -as [type])) {
                            Add-Type @"
using System; using System.Runtime.InteropServices;
public static class DeskPilotRecycleClose {
  [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
"@
                        }
                        if ([DeskPilotRecycleClose]::IsWindow([IntPtr]$hwnd) -and [DeskPilotRecycleClose]::PostMessage([IntPtr]$hwnd,0x0010,[IntPtr]::Zero,[IntPtr]::Zero)) { $closed++ }
                    } catch {}
                }
                if ($closed -eq 0) { try { $w.Quit(); $closed++ } catch {} }
            }
        } catch {}
    }
} catch {}

# Fallback: close a visible top-level window whose title identifies Recycle Bin.
if ($closed -eq 0) {
    Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class DeskPilotRecycleBinWin32 {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
"@
    $WM_CLOSE = 0x0010
    [DeskPilotRecycleBinWin32]::EnumWindows({ param($h,$l)
        if (-not [DeskPilotRecycleBinWin32]::IsWindowVisible($h)) { return $true }
        $sb = New-Object System.Text.StringBuilder 512
        [void][DeskPilotRecycleBinWin32]::GetWindowText($h,$sb,$sb.Capacity)
        $title = $sb.ToString()
        if ($title -match '(?i)Recycle Bin') {
            if ([DeskPilotRecycleBinWin32]::PostMessage($h,$WM_CLOSE,[IntPtr]::Zero,[IntPtr]::Zero)) { $script:closed++ }
        }
        return $true
    },[IntPtr]::Zero) | Out-Null
}
[PSCustomObject]@{closed=$closed} | ConvertTo-Json -Compress
'''
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "Unknown error").strip()
                raise RuntimeError(f"Could not close Recycle Bin: {detail}")
            try:
                import json
                data = json.loads((result.stdout or "{}").strip() or "{}")
                closed = int(data.get("closed", 0))
            except Exception:
                closed = 0
            if closed:
                return {"message": "Recycle Bin closed successfully.", "closed": closed}
            return {"message": "Recycle Bin is not currently open.", "closed": 0}

        if action in {"open", "open_and_count"}:
            subprocess.Popen(
                ["explorer.exe", "shell:RecycleBinFolder"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

        if action == "open":
            return {"message": "Recycle Bin opened successfully.", "files": 0, "folders": 0, "total": 0}

        # Shell.Application namespace 10 is the Windows Recycle Bin. This avoids
        # relying on the protected C:\$Recycle.Bin folders or user SID.
        ps = (
            "$shell=New-Object -ComObject Shell.Application; "
            "$bin=$shell.Namespace(10); "
            "$files=0; $folders=0; "
            "if ($bin) { foreach ($item in $bin.Items()) { if ($item.IsFolder) { $folders++ } else { $files++ } } }; "
            "[PSCustomObject]@{files=$files;folders=$folders;total=($files+$folders)} | ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            raw = (result.stdout or result.stderr).strip()
            import json
            data = json.loads(raw) if raw else {"files": 0, "folders": 0, "total": 0}
            files = int(data.get("files", 0)); folders = int(data.get("folders", 0)); total = int(data.get("total", files + folders))
        except Exception as exc:
            raise RuntimeError(f"Could not read Recycle Bin: {exc}")

        return {
            "message": f"Recycle Bin contains {total} item(s): {files} file(s) and {folders} folder(s).",
            "files": files, "folders": folders, "total": total,
        }

    def open_file_explorer(
        self
    ):

        subprocess.Popen(
            [
                "explorer.exe"
            ]
        )

        return (
            "File Explorer opened successfully."
        )

    
    # OPEN THIS PC
    

    def open_this_pc(
        self
    ):

        subprocess.Popen(
            [
                "explorer.exe",
                "shell:MyComputerFolder"
            ]
        )

        return (
            "This PC opened successfully."
        )

    
    # OPEN KNOWN FOLDER
    

    def open_folder(
        self,
        location
    ):

        location = self.normalize_location(
            location
        )

        folder = self.get_location(
            location
        )

        if not folder.exists():

            raise FileNotFoundError(
                f"{location.title()} folder "
                f"does not exist."
            )

        os.startfile(
            str(folder)
        )

        return (
            f"{location.title()} "
            f"opened successfully."
        )

    
    # OPEN EXACT ITEM / PATH
    

    def open_item(
        self,
        item_name,
        location
    ):

        base_folder = self.get_location(
            location
        )

        item_path = self._safe_child(
            base_folder,
            item_name
        )

        if not item_path.exists():

            raise FileNotFoundError(
                f"'{item_name}' was not found "
                f"in {location.title()}."
            )

        os.startfile(
            str(item_path)
        )

        return (
            f"'{item_name}' opened successfully."
        )

    
    # LIST FILES / FOLDERS
    

    def list_files(
        self,
        location
    ):

        folder = self.get_location(
            location
        )

        if not folder.exists():
            return []

        items = []

        for item in sorted(
            folder.iterdir(),
            key=lambda path: path.name.lower()
        ):

            item_type = (
                "Folder"
                if item.is_dir()
                else "File"
            )

            items.append(
                {
                    "name": item.name,
                    "type": item_type,
                    "path": str(item),
                }
            )

        return items

    
    # SEARCH HELPERS

    @staticmethod
    def _search_text(value):
        """Normalize a human filename query for forgiving matching.

        Spaces, underscores, hyphens, dots and other punctuation are treated
        as separators so users do not need to know the exact filename format.
        """
        value = str(value or "").casefold()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _query_tokens(cls, query):
        """Turn a natural search phrase into useful filename terms."""
        text = cls._search_text(query)
        filler = {
            "find", "search", "look", "lookup", "locate", "show",
            "get", "open", "where", "is", "my", "me", "please",
            "file", "files", "folder", "folders", "item", "items",
            "document", "documents",
        }
        tokens = [t for t in text.split() if t not in filler]

        # Common human descriptions -> filename vocabulary.
        aliases = {
            "resume": {"resume", "cv"},
            "curriculum": {"curriculum", "cv", "vitae"},
            "vitae": {"vitae", "cv", "resume"},
            "cv": {"cv", "resume"},
            "photo": {"photo", "photos", "image", "images", "pic", "pics"},
            "photos": {"photos", "photo", "images", "image", "pics", "pic"},
            "picture": {"picture", "pictures", "image", "images", "photo", "photos"},
            "pictures": {"pictures", "picture", "images", "image", "photos", "photo"},
        }

        expanded = []
        for token in tokens:
            expanded.append(aliases.get(token, {token}))
        return tokens, expanded

    @classmethod
    def _filename_match_score(cls, query, filename):
        """Return a 0..1 relevance score for forgiving natural-language search."""
        q = cls._search_text(query)
        name = cls._search_text(filename)

        if not q or not name:
            return 0.0

        if q == name:
            return 1.0
        if q in name:
            return 0.96

        q_tokens, expanded = cls._query_tokens(query)
        name_tokens = name.split()
        if not q_tokens:
            return 0.0

        # Every requested concept must have a reasonably close filename token.
        concept_scores = []
        for choices in expanded:
            best = 0.0
            for wanted in choices:
                for actual in name_tokens:
                    if wanted == actual:
                        best = max(best, 1.0)
                    elif wanted in actual or actual in wanted:
                        best = max(best, 0.90)
                    else:
                        best = max(best, SequenceMatcher(None, wanted, actual).ratio())
            concept_scores.append(best)

        if concept_scores and min(concept_scores) >= 0.72:
            return min(0.95, sum(concept_scores) / len(concept_scores))

        # Compact comparison handles spaces/underscores/hyphens and small typos.
        compact_q = q.replace(" ", "")
        compact_name = name.replace(" ", "")
        ratio = SequenceMatcher(None, compact_q, compact_name).ratio()
        # For multi-word searches, never let one matching word  make an unrelated filename rank as
        # a strong match.  A fuzzy single-token fallback is useful only when
        # the user actually searched for one token.
        if len(q_tokens) == 1:
            token_ratio = max(
                (SequenceMatcher(None, q_tokens[0], nt).ratio()
                 for nt in name_tokens),
                default=0.0,
            )
            return max(ratio, token_ratio * 0.92)

        return ratio

    # FIND / SEARCH FILE OR FOLDER

    def find_item(
        self,
        query,
        location,
        item_type=None,
        recursive=True,
        limit=50
    ):

        normalized_location = self.normalize_location(location)
        if normalized_location == "computer":
            roots = [p for p in self.search_roots if p.exists()]
        else:
            base_folder = self.get_location(normalized_location)
            roots = [base_folder] if base_folder.exists() else []

        if not roots:
            raise FileNotFoundError(
                f"{location.title()} does not exist or is unavailable."
            )

        query = str(query).strip()
        if not query:
            raise ValueError("Search query cannot be empty.")

        # If the user supplied an extension (for example .txt), do not
        # return a different file type merely because its name is similar.
        requested_extension = ""
        query_path = Path(query)
        if query_path.suffix and re.fullmatch(r"\.[A-Za-z0-9]{1,8}", query_path.suffix):
            requested_extension = query_path.suffix.casefold()

        normalized_type = None
        if item_type:
            normalized_type = str(item_type).strip().lower()
            if normalized_type in {"", "null", "none", "any"}:
                normalized_type = None
            elif normalized_type not in {"file", "folder"}:
                raise ValueError("item_type must be 'file' or 'folder'.")

        matches = []
        seen = set()
        try:
            for root in roots:
                iterator = root.rglob("*") if recursive else root.iterdir()
                for item in iterator:
                    try:
                        if normalized_type == "file" and not item.is_file():
                            continue
                        if normalized_type == "folder" and not item.is_dir():
                            continue
                        if requested_extension and item.is_file() and item.suffix.casefold() != requested_extension:
                            continue

                        score = self._filename_match_score(query, item.name)
                        if score < 0.55:
                            continue

                        path_key = str(item).casefold()
                        if path_key in seen:
                            continue
                        seen.add(path_key)

                        matches.append({
                            "name": item.name,
                            "type": "Folder" if item.is_dir() else "File",
                            "path": str(item),
                            "score": round(score, 3),
                        })
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass

        # Best filename matches first, then shortest names/paths for ties.
        matches.sort(key=lambda row: (-row["score"], len(row["name"]), row["name"].casefold()))
        return matches[:limit]

    
    # FIND FILES BY EXTENSION
    

    def find_by_extension(
        self,
        extension,
        location,
        recursive=True,
        limit=50
    ):
        normalized_location = self.normalize_location(location)
        if normalized_location == "computer":
            roots = [p for p in self.search_roots if p.exists()]
        else:
            base_folder = self.get_location(normalized_location)
            roots = [base_folder] if base_folder.exists() else []

        extension = str(extension).strip().lower()
        if not extension.startswith("."):
            extension = "." + extension

        results = []
        try:
            for root in roots:
                iterator = root.rglob("*") if recursive else root.iterdir()
                for item in iterator:
                    try:
                        if not item.is_file() or item.suffix.lower() != extension:
                            continue
                        results.append({
                            "name": item.name,
                            "type": "File",
                            "path": str(item),
                            "modified": item.stat().st_mtime,
                        })
                        if len(results) >= limit:
                            return results
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return results

    
    # FIND LATEST FILE
    

    def find_latest_file(
        self,
        location,
        extension=None
    ):
        normalized_location = self.normalize_location(location)
        if normalized_location == "computer":
            roots = [p for p in self.search_roots if p.exists()]
        else:
            root = self.get_location(normalized_location)
            roots = [root] if root.exists() else []

        normalized_extensions = None
        if extension:
            raw_extensions = extension if isinstance(extension, (list, tuple, set)) else str(extension).replace(";", ",").split(",")
            normalized_extensions = set()
            for ext in raw_extensions:
                ext = str(ext).strip().lower()
                if not ext:
                    continue
                if not ext.startswith("."):
                    ext = "." + ext
                normalized_extensions.add(ext)
            if not normalized_extensions:
                normalized_extensions = None

        files = []
        for root in roots:
            try:
                for item in root.rglob("*"):
                    try:
                        if not item.is_file():
                            continue
                        if normalized_extensions and item.suffix.lower() not in normalized_extensions:
                            continue
                        files.append(item)
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue

        if not files:
            return None

        latest = max(files, key=lambda path: path.stat().st_mtime)
        return {
            "name": latest.name,
            "type": "File",
            "path": str(latest),
            "modified": latest.stat().st_mtime,
        }

    
    # CREATE FOLDER
    

    def create_folder(
        self,
        folder_name,
        location="desktop"
    ):

        base_folder = self.get_location(
            location
        )

        if not base_folder.exists():

            raise FileNotFoundError(
                f"{location.title()} "
                f"does not exist."
            )

        folder_path = self._safe_child(
            base_folder,
            folder_name
        )

        if folder_path.exists():

            return (
                f"'{folder_name}' already exists "
                f"in {location.title()}."
            )

        folder_path.mkdir()

        return (
            f"Folder '{folder_name}' created "
            f"in {location.title()}."
        )

    
    # CREATE FILE
    

    def create_file(
        self,
        file_name,
        location="desktop",
        content=""
    ):

        base_folder = self.get_location(
            location
        )

        if not base_folder.exists():

            raise FileNotFoundError(
                f"{location.title()} "
                f"does not exist."
            )

        file_path = self._safe_child(
            base_folder,
            file_name
        )

        if file_path.exists():

            return (
                f"'{file_name}' already exists "
                f"in {location.title()}."
            )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"File '{file_name}' created "
            f"in {location.title()}."
        )

    
    # RENAME FILE / FOLDER
    

    def rename_item(
        self,
        old_name,
        new_name,
        location
    ):

        base_folder = self.get_location(
            location
        )

        old_path = self._safe_child(
            base_folder,
            old_name
        )

        new_path = self._safe_child(
            base_folder,
            new_name
        )

        if not old_path.exists():

            raise FileNotFoundError(
                f"'{old_name}' was not found "
                f"in {location.title()}."
            )

        if new_path.exists():

            raise FileExistsError(
                f"'{new_name}' already exists."
            )

        old_path.rename(
            new_path
        )

        return (
            f"'{old_name}' renamed to "
            f"'{new_name}'."
        )

    
    # COPY FILE / FOLDER
    

    def copy_item(
        self,
        item_name,
        source_location,
        destination_location
    ):

        source_folder = self.get_location(
            source_location
        )

        destination_folder = self.get_location(
            destination_location
        )

        source_path = self._safe_child(
            source_folder,
            item_name
        )

        destination_path = self._safe_child(
            destination_folder,
            item_name
        )

        if not source_path.exists():

            raise FileNotFoundError(
                f"'{item_name}' was not found "
                f"in {source_location.title()}."
            )

        if destination_path.exists():

            raise FileExistsError(
                f"'{item_name}' already exists "
                f"in {destination_location.title()}."
            )

        if source_path.is_dir():

            shutil.copytree(
                source_path,
                destination_path
            )

        else:

            shutil.copy2(
                source_path,
                destination_path
            )

        return (
            f"'{item_name}' copied from "
            f"{source_location.title()} "
            f"to {destination_location.title()}."
        )

    
    # MOVE FILE / FOLDER
    

    def move_item(
        self,
        item_name,
        source_location,
        destination_location
    ):

        source_folder = self.get_location(
            source_location
        )

        destination_folder = self.get_location(
            destination_location
        )

        source_path = self._safe_child(
            source_folder,
            item_name
        )

        destination_path = self._safe_child(
            destination_folder,
            item_name
        )

        if not source_path.exists():

            raise FileNotFoundError(
                f"'{item_name}' was not found "
                f"in {source_location.title()}."
            )

        if destination_path.exists():

            raise FileExistsError(
                f"'{item_name}' already exists "
                f"in {destination_location.title()}."
            )

        shutil.move(
            str(source_path),
            str(destination_path)
        )

        return (
            f"'{item_name}' moved from "
            f"{source_location.title()} "
            f"to {destination_location.title()}."
        )
        
    # IMAGE EXTENSIONS
    

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".heic",
        ".heif",
    }

    
    # COUNT IMAGES
    

    def count_images(
        self,
        location="pictures",
        recursive=True
    ):
        location = self.normalize_location(location)

        if location == "computer":
            roots = [p for p in self.search_roots if p.exists()]
        else:
            root = self.get_location(location)
            roots = [root] if root.exists() else []

        total = 0
        seen_files = set()

        for root in roots:
            try:
                iterator = root.rglob("*") if recursive else root.glob("*")
                for item in iterator:
                    try:
                        if not item.is_file() or item.suffix.lower() not in self.IMAGE_EXTENSIONS:
                            continue
                        resolved = str(item.resolve()).lower()
                        if resolved in seen_files:
                            continue
                        seen_files.add(resolved)
                        total += 1
                    except (PermissionError, OSError):
                        continue
            except (PermissionError, OSError):
                continue

        return total

