import os
import shutil
import subprocess

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

    # =========================================================
    # FIND WINDOWS USER FOLDER
    # =========================================================

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

    # =========================================================
    # NORMALIZE LOCATION
    # =========================================================

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
        }

        return aliases.get(
            location,
            location
        )

    # =========================================================
    # RESOLVE LOCATION
    # =========================================================

    def get_location(
        self,
        location
    ):

        location = self.normalize_location(
            location
        )

        path = self.allowed_locations.get(
            location
        )

        if path is None:

            supported = ", ".join(
                self.allowed_locations.keys()
            )

            raise ValueError(
                f"Unknown location '{location}'. "
                f"Supported locations: {supported}"
            )

        return path

    # =========================================================
    # SAFETY
    # =========================================================

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

    # =========================================================
    # OPEN FILE EXPLORER
    # =========================================================

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

    # =========================================================
    # OPEN THIS PC
    # =========================================================

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

    # =========================================================
    # OPEN KNOWN FOLDER
    # =========================================================

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

    # =========================================================
    # OPEN EXACT ITEM / PATH
    # =========================================================

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

    # =========================================================
    # LIST FILES / FOLDERS
    # =========================================================

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

    # =========================================================
    # FIND / SEARCH FILE OR FOLDER
    # =========================================================

    def find_item(
        self,
        query,
        location,
        item_type=None,
        recursive=True,
        limit=50
    ):

        base_folder = self.get_location(
            location
        )

        if not base_folder.exists():

            raise FileNotFoundError(
                f"{location.title()} "
                f"does not exist."
            )

        query = (
            query
            .strip()
            .lower()
        )

        if not query:

            raise ValueError(
                "Search query cannot be empty."
            )

        normalized_type = None

        if item_type:

            normalized_type = (
                item_type
                .strip()
                .lower()
            )

            if normalized_type not in {
                "file",
                "folder"
            }:

                raise ValueError(
                    "item_type must be "
                    "'file' or 'folder'."
                )

        if recursive:

            iterator = (
                base_folder.rglob("*")
            )

        else:

            iterator = (
                base_folder.iterdir()
            )

        matches = []

        try:

            for item in iterator:

                try:

                    if (
                        query
                        not in
                        item.name.lower()
                    ):
                        continue

                    if (
                        normalized_type == "file"
                        and
                        not item.is_file()
                    ):
                        continue

                    if (
                        normalized_type == "folder"
                        and
                        not item.is_dir()
                    ):
                        continue

                    matches.append(
                        {
                            "name": item.name,
                            "type": (
                                "Folder"
                                if item.is_dir()
                                else "File"
                            ),
                            "path": str(item),
                        }
                    )

                    if len(matches) >= limit:
                        break

                except (
                    PermissionError,
                    OSError
                ):
                    continue

        except (
            PermissionError,
            OSError
        ):
            pass

        return matches

    # =========================================================
    # FIND FILES BY EXTENSION
    # =========================================================

    def find_by_extension(
        self,
        extension,
        location,
        recursive=True,
        limit=50
    ):

        base_folder = self.get_location(
            location
        )

        if not base_folder.exists():

            return []

        extension = (
            extension
            .strip()
            .lower()
        )

        if not extension.startswith("."):

            extension = (
                "."
                + extension
            )

        if recursive:

            iterator = base_folder.rglob(
                "*"
            )

        else:

            iterator = base_folder.iterdir()

        results = []

        for item in iterator:

            try:

                if not item.is_file():
                    continue

                if (
                    item.suffix.lower()
                    != extension
                ):
                    continue

                results.append(
                    {
                        "name": item.name,
                        "type": "File",
                        "path": str(item),
                        "modified": (
                            item.stat()
                            .st_mtime
                        ),
                    }
                )

                if len(results) >= limit:
                    break

            except (
                PermissionError,
                OSError
            ):
                continue

        return results

    # =========================================================
    # FIND LATEST FILE
    # =========================================================

    def find_latest_file(
        self,
        location,
        extension=None
    ):

        base_folder = self.get_location(
            location
        )

        if not base_folder.exists():
            return None

        files = []

        for item in base_folder.rglob(
            "*"
        ):

            try:

                if not item.is_file():
                    continue

                if extension:

                    normalized_extension = (
                        extension
                        .lower()
                        .strip()
                    )

                    if not normalized_extension.startswith(
                        "."
                    ):

                        normalized_extension = (
                            "."
                            + normalized_extension
                        )

                    if (
                        item.suffix.lower()
                        != normalized_extension
                    ):

                        continue

                files.append(
                    item
                )

            except (
                PermissionError,
                OSError
            ):
                continue

        if not files:
            return None

        latest = max(
            files,
            key=lambda path: (
                path.stat()
                .st_mtime
            )
        )

        return {
            "name": latest.name,
            "type": "File",
            "path": str(latest),
            "modified": (
                latest.stat()
                .st_mtime
            ),
        }

    # =========================================================
    # CREATE FOLDER
    # =========================================================

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

    # =========================================================
    # CREATE FILE
    # =========================================================

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

    # =========================================================
    # RENAME FILE / FOLDER
    # =========================================================

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

    # =========================================================
    # COPY FILE / FOLDER
    # =========================================================

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

    # =========================================================
    # MOVE FILE / FOLDER
    # =========================================================

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