import re
import os
class ToolExecutor:

    # SUPPORTED TOOLS

    ALLOWED_TOOLS = {
        "open_file_explorer",
        "open_this_pc",

        "open_app",

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

        "open_app",
        "close_app",
        "close_window",
        "get_app_info",
        "check_app_status",
        "count_images",

        "browser_open",
        "browser_search",
        "browser_close",

        "check_running_apps",
        "get_window_info",
        "open_url",

        "unknown",
    }

    # SAFE FILE LOCATIONS

    ALLOWED_LOCATIONS = {
        "desktop",
        "downloads",
        "documents",
        "pictures",
        "videos",
    }

    SEARCH_LOCATIONS = {
        "desktop", "downloads", "documents", "pictures", "videos", "computer"
    }

    # SUPPORTED BROWSER SITES

    ALLOWED_BROWSER_SITES = {
        "google",
        "youtube",
        "github",
        "bing",
        "wikipedia",
        "duckduckgo",
    }

    # BROWSER ALIASES

    BROWSER_ALIASES = {
        "yt": "youtube",
        "wiki": "wikipedia",
        "ddg": "duckduckgo",
    }

    # INIT

    def __init__(
        self,
        file_agent,
        app_agent,
        browser_open_callback=None,
        browser_search_callback=None,
        browser_close_callback=None,
    ):

        self.file_agent = file_agent
        self.app_agent = app_agent

        self.browser_open_callback = (
            browser_open_callback
        )

        self.browser_search_callback = (
            browser_search_callback
        )

        self.browser_close_callback = (
            browser_close_callback
        )

    # MAIN EXECUTOR

    def execute(
        self,
        plan
    ):


        # VALIDATE PLAN


        if not isinstance(
            plan,
            dict
        ):

            raise ValueError(
                "Planner output must be a dictionary."
            )

        tool = plan.get(
            "tool"
        )

        args = plan.get(
            "args",
            {}
        )

        if not isinstance(
            tool,
            str
        ):

            raise ValueError(
                "Planner output does not contain "
                "a valid tool."
            )

        if not isinstance(
            args,
            dict
        ):

            raise ValueError(
                "Planner args must be a dictionary."
            )

        tool = tool.strip()

        if tool not in self.ALLOWED_TOOLS:

            raise ValueError(
                f"Tool '{tool}' is not allowed."
            )

        # CLOSE APP


        if tool == "close_app":

            app_name = (
                args.get(
                    "app_name"
                )
            )

            if not app_name:

                raise ValueError(
                    "App name is required."
                )

            message = (
                self.app_agent
                .close_app(
                    app_name
                )
            )

            return self._result(
                message=message
            )


        # CLOSE WINDOW / FILE / FOLDER


        if tool == "close_window":

            target = args.get("target") or args.get("item_name") or args.get("name")
            if not target:
                raise ValueError("Window, file, or folder name is required.")

            message = self.app_agent.close_window(target)
            return self._result(message=message)


        # GET APP INFO


        if tool == "get_app_info":

            app_name = args.get("app_name")
            if not app_name:
                raise ValueError("App name is required.")

            info = self.app_agent.get_app_info(app_name)
            if not info.get("found"):
                message = f"I could not find an installed application named '{app_name}'."
            else:
                location = info.get("executable_path") or info.get("location") or info.get("shortcut_path")
                message = f"{info.get('name') or app_name} is installed."
                if location:
                    message += f"\nLocation: {location}"

            return self._result(message=message, data=info)


        # CHECK APP STATUS


        if tool == "check_app_status":

            app_name = args.get("app_name")
            if not app_name:
                raise ValueError("App name is required.")

            status = self.app_agent.check_app_status(app_name)

            if status.get("running"):
                process_names = ", ".join(status.get("process_names") or [])
                message = f"{app_name} is currently running."
                if process_names:
                    message += f" Process: {process_names}."
            elif status.get("installed"):
                message = (
                    f"{app_name} is installed, but it is not currently running. "
                    "I can try to open it if you want."
                )
            else:
                message = (
                    f"I could not find {app_name} as an installed or running app "
                    "on this PC."
                )

            return self._result(
                message=message,
                data=status
            )


        # COUNT IMAGES


        if tool == "count_images":

            location = (
                args.get(
                    "location",
                    "pictures"
                )
            )

            recursive = (
                args.get(
                    "recursive",
                    True
                )
            )

            count = (
                self.file_agent
                .count_images(
                    location=location,
                    recursive=recursive
                )
            )

            if location in {
                "system",
                "computer",
                "pc",
                "my pc",
            }:

                message = (
                    f"You have {count} image files "
                    f"across your main user folders."
                )

            else:

                message = (
                    f"There are {count} image files "
                    f"in the {location.title()} folder."
                )

            return self._result(
                message=message,
                data={
                    "count": count,
                    "location": location,
                }
            )

        # UNKNOWN


        if tool == "unknown":

            reason = args.get(
                "reason",
                "I don't know how to perform "
                "that action yet."
            )

            return self._result(
                message=str(reason)
            )


        # OPEN FILE EXPLORER


        if tool == "open_file_explorer":

            message = (
                self.file_agent
                .open_file_explorer()
            )

            return self._result(
                message=message
            )


        # OPEN THIS PC


        if tool == "open_this_pc":

            message = (
                self.file_agent
                .open_this_pc()
            )

            return self._result(
                message=message
            )


        # OPEN WINDOWS APP


        if tool == "open_app":

            self._require(
                args,
                "app_name"
            )

            app_name = self._clean_text(
                args["app_name"],
                "app_name"
            )

            message = (
                self.app_agent
                .open_app(
                    app_name
                )
            )

            return self._result(
                message=message
            )


        # OPEN FOLDER


        if tool == "open_folder":

            location = self._get_location(
                args
            )

            message = (
                self.file_agent
                .open_folder(
                    location
                )
            )

            return self._result(
                message=message
            )


        # OPEN FILE / FOLDER ITEM


        if tool == "open_item":

            self._require(
                args,
                "item_name",
                "location"
            )

            item_name = self._clean_text(
                args["item_name"],
                "item_name"
            )

            location = self._validate_search_location(
                args["location"]
            )

            message = (
                self.file_agent
                .open_item(
                    item_name=item_name,
                    location=location,
                )
            )

            return self._result(
                message=message
            )


        # LIST FILES


        if tool == "list_files":

            location = self._get_location(
                args
            )

            items = (
                self.file_agent
                .list_files(
                    location
                )
            )

            message = self._format_items(
                items=items,
                title=location.title(),
            )

            return self._result(
                message=message,
                data=items,
            )


        # FIND ITEM


        if tool == "find_item":

            self._require(
                args,
                "query",
                "location"
            )

            query = self._clean_text(
                args["query"],
                "query"
            )

            location = self._validate_search_location(
                args["location"]
            )

            item_type = args.get(
                "item_type"
            )

            if item_type is not None:

                item_type = (
                    str(item_type)
                    .lower()
                    .strip()
                )

                if item_type in {
                    "",
                    "null",
                    "none",
                    "any",
                }:

                    item_type = None

                elif item_type not in {
                    "file",
                    "folder",
                }:

                    raise ValueError(
                        "item_type must be "
                        "'file', 'folder' or null."
                    )

            results = (
                self.file_agent
                .find_item(
                    query=query,
                    location=location,
                    item_type=item_type,
                )
            )

            # A compound command such as "search X file and open that"
            # should search first, then open the best matching result.
            # Never try to open the raw query as a literal filename.
            if results and args.get("open_result") is True:
                selected = results[0]
                selected_path = selected.get("path")
                if selected_path and os.path.isfile(selected_path):
                    os.startfile(selected_path)
                    return self._result(
                        message=(
                            f"Found and opened '{selected['name']}'.\n"
                            f"{selected_path}"
                        ),
                        data={"selected": selected, "matches": results},
                    )

            if not results:

                message = (
                    f"No matching item found for "
                    f"'{query}' in "
                    f"{location.title()}."
                )

            else:

                message = self._format_items(
                    items=results,
                    title=(
                        f"Search results for "
                        f"'{query}'"
                    ),
                )

            return self._result(
                message=message,
                data=results,
            )


        # FIND FILES BY EXTENSION


        if tool == "find_by_extension":

            self._require(
                args,
                "extension",
                "location"
            )

            extension = self._clean_text(
                args["extension"],
                "extension"
            )

            location = (
                self._validate_search_location(
                    args["location"]
                )
            )

            results = (
                self.file_agent
                .find_by_extension(
                    extension=extension,
                    location=location,
                )
            )

            # Explicit "open <extension> files" commands mean open every
            # matching file returned by the extension search.  Do not route
            # this through fuzzy find_item(), and never open a different
            # extension just because its filename looks similar.
            if results and args.get("open_results") is True:
                opened = []
                failed = []
                for item in results:
                    path = item.get("path")
                    if not path:
                        continue
                    try:
                        if os.path.isfile(path):
                            os.startfile(path)
                            opened.append(item)
                    except OSError:
                        failed.append(item)

                if not opened:
                    return self._result(
                        message=(
                            f"Found {len(results)} {extension} file(s), "
                            "but none could be opened."
                        ),
                        data=results,
                    )

                message = (
                    f"Found and opened {len(opened)} {extension} file(s) "
                    f"in {location.title()}.\n"
                    + "\n".join(
                        f"{item['name']}\n{item['path']}"
                        for item in opened
                    )
                )
                if failed:
                    message += f"\n{len(failed)} file(s) could not be opened."
                return self._result(message=message, data=opened)

            if not results:

                message = (
                    f"No {extension} files found "
                    f"in {location.title()}."
                )

            else:

                message = self._format_items(
                    items=results,
                    title=(
                        f"{extension} files in "
                        f"{location.title()}"
                    ),
                )

            return self._result(
                message=message,
                data=results,
            )


        # FIND LATEST FILE


        if tool == "find_latest_file":

            self._require(args, "location")
            location = self._validate_search_location(
                args["location"]
            )

            extension = args.get(
                "extension"
            )

            if extension is not None:

                extension = (
                    str(extension)
                    .strip()
                )

                if extension.lower() in {
                    "",
                    "null",
                    "none",
                    "any",
                }:

                    extension = None

            result = (
                self.file_agent
                .find_latest_file(
                    location=location,
                    extension=extension,
                )
            )

            if result is None:

                message = (
                    f"No matching file found "
                    f"in {location.title()}."
                )

            else:

                message = (
                    "Latest file found:\n"
                    f"{result['name']}\n"
                    f"{result['path']}"
                )

            return self._result(
                message=message,
                data=result,
            )


        # CREATE FOLDER


        if tool == "create_folder":

            self._require(
                args,
                "folder_name",
                "location"
            )

            folder_name = self._clean_text(
                args["folder_name"],
                "folder_name"
            )

            location = (
                self._validate_location(
                    args["location"]
                )
            )

            message = (
                self.file_agent
                .create_folder(
                    folder_name=folder_name,
                    location=location,
                )
            )

            return self._result(
                message=message
            )


        # CREATE FILE


        if tool == "create_file":

            self._require(
                args,
                "file_name",
                "location"
            )

            file_name = self._clean_text(
                args["file_name"],
                "file_name"
            )

            location = (
                self._validate_location(
                    args["location"]
                )
            )

            content = args.get(
                "content",
                ""
            )

            if content is None:
                content = ""

            content = str(
                content
            )

            message = (
                self.file_agent
                .create_file(
                    file_name=file_name,
                    location=location,
                    content=content,
                )
            )

            return self._result(
                message=message
            )


        # RENAME ITEM


        if tool == "rename_item":

            self._require(
                args,
                "old_name",
                "new_name",
                "location"
            )

            old_name = self._clean_text(
                args["old_name"],
                "old_name"
            )

            new_name = self._clean_text(
                args["new_name"],
                "new_name"
            )

            location = (
                self._validate_location(
                    args["location"]
                )
            )

            message = (
                self.file_agent
                .rename_item(
                    old_name=old_name,
                    new_name=new_name,
                    location=location,
                )
            )

            return self._result(
                message=message
            )


        # COPY ITEM


        if tool == "copy_item":

            self._require(
                args,
                "item_name",
                "source_location",
                "destination_location"
            )

            item_name = self._clean_text(
                args["item_name"],
                "item_name"
            )

            source = (
                self._validate_location(
                    args["source_location"]
                )
            )

            destination = (
                self._validate_location(
                    args[
                        "destination_location"
                    ]
                )
            )

            message = (
                self.file_agent
                .copy_item(
                    item_name=item_name,
                    source_location=source,
                    destination_location=destination,
                )
            )

            return self._result(
                message=message
            )


        # MOVE ITEM


        if tool == "move_item":

            self._require(
                args,
                "item_name",
                "source_location",
                "destination_location"
            )

            item_name = self._clean_text(
                args["item_name"],
                "item_name"
            )

            source = (
                self._validate_location(
                    args["source_location"]
                )
            )

            destination = (
                self._validate_location(
                    args[
                        "destination_location"
                    ]
                )
            )

            message = (
                self.file_agent
                .move_item(
                    item_name=item_name,
                    source_location=source,
                    destination_location=destination,
                )
            )

            return self._result(
                message=message
            )


        # BROWSER OPEN


        if tool == "browser_open":

            self._require(
                args,
                "site"
            )

            site = self._validate_site(
                args["site"]
            )

            if (
                self.browser_open_callback
                is None
            ):

                raise RuntimeError(
                    "Browser open callback "
                    "is not configured."
                )

            self.browser_open_callback(
                site
            )

            return self._result(
                message=None,
                asynchronous=True,
            )


        # BROWSER SEARCH


        if tool == "browser_search":

            self._require(
                args,
                "site",
                "query"
            )

            site = self._validate_site(
                args["site"]
            )

            query = self._clean_text(
                args["query"],
                "query"
            )

            if (
                self.browser_search_callback
                is None
            ):

                raise RuntimeError(
                    "Browser search callback "
                    "is not configured."
                )

            self.browser_search_callback(
                site,
                query
            )

            return self._result(
                message=None,
                asynchronous=True,
            )


        # BROWSER CLOSE


        if tool == "browser_close":

            self._require(
                args,
                "site"
            )

            site = self._validate_site(
                args["site"]
            )

            if (
                self.browser_close_callback
                is None
            ):

                raise RuntimeError(
                    "Browser close callback "
                    "is not configured."
                )

            self.browser_close_callback(
                site
            )

            return self._result(
                message=None,
                asynchronous=True,
            )


        # FALLBACK


        raise RuntimeError(
            f"Tool '{tool}' could not be executed."
        )

    # RESULT FORMAT

    def _result(
        self,
        message=None,
        data=None,
        asynchronous=False,
    ):

        return {
            "success": True,
            "message": message,
            "data": data,
            "asynchronous": asynchronous,
        }

    # REQUIRED ARGUMENT CHECK

    def _require(
        self,
        args,
        *names
    ):

        missing = []

        for name in names:

            if name not in args:

                missing.append(
                    name
                )

                continue

            value = args.get(
                name
            )

            if value is None:

                missing.append(
                    name
                )

                continue

            if (
                isinstance(
                    value,
                    str
                )
                and
                not value.strip()
            ):

                missing.append(
                    name
                )

        if missing:

            raise ValueError(
                "Missing required argument(s): "
                + ", ".join(
                    missing
                )
            )

    # CLEAN TEXT

    def _clean_text(
        self,
        value,
        name
    ):

        if value is None:

            raise ValueError(
                f"{name} is required."
            )

        value = str(
            value
        ).strip()

        if not value:

            raise ValueError(
                f"{name} cannot be empty."
            )

        return value

    # GET LOCATION

    def _get_location(
        self,
        args
    ):

        self._require(
            args,
            "location"
        )

        return self._validate_location(
            args["location"]
        )

    # VALIDATE SEARCH LOCATION

    def _validate_search_location(self, location):
        location = self._clean_text(location, "location")
        aliases = {
            "desktop": "desktop",
            "destop": "desktop",
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
        normalized = aliases.get(location.lower(), location.lower())
        if re.fullmatch(r"[a-z]:", normalized, re.IGNORECASE):
            return normalized.upper()
        if normalized not in self.SEARCH_LOCATIONS:
            raise ValueError(f"Search location '{location}' is not currently allowed.")
        return normalized

    # VALIDATE LOCATION

    def _validate_location(
        self,
        location
    ):

        location = self._clean_text(
            location,
            "location"
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

        normalized = aliases.get(
            location.lower(),
            location.lower()
        )

        if (
            normalized
            not in
            self.ALLOWED_LOCATIONS
        ):

            raise ValueError(
                f"Location '{location}' "
                f"is not currently allowed."
            )

        return normalized

    # VALIDATE BROWSER SITE

    def _validate_site(
        self,
        site
    ):

        site = (
            self._clean_text(
                site,
                "site"
            )
            .lower()
        )

        site = self.BROWSER_ALIASES.get(
            site,
            site
        )

        if (
            site
            not in
            self.ALLOWED_BROWSER_SITES
        ):

            raise ValueError(
                f"Browser site '{site}' "
                f"is not currently supported."
            )

        return site

    # FORMAT FILE RESULTS

    def _format_items(
        self,
        items,
        title=None,
        limit=30,
    ):

        if not items:

            if title:

                return (
                    f"No items found in {title}."
                )

            return "No items found."

        lines = []

        if title:

            lines.append(
                title
            )

        for item in items[:limit]:

            item_type = item.get(
                "type",
                "Item"
            )

            name = item.get(
                "name",
                "Unknown"
            )

            path = item.get(
                "path"
            )

            if path:

                lines.append(
                    f"{item_type}: "
                    f"{name}\n"
                    f"{path}"
                )

            else:

                lines.append(
                    f"{item_type}: "
                    f"{name}"
                )

        if len(items) > limit:

            lines.append(
                f"... and "
                f"{len(items) - limit} more."
            )

        return "\n".join(
            lines
        )