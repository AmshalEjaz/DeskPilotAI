import sys
import re
import html
import queue

from automation.browser_agent import BrowserAgent
from automation.file_agent import FileAgent
from automation.app_agent import AppAgent
from automation.planner_agent import PlannerAgent
from automation.tool_executor import ToolExecutor

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
)

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QFrame,
)



# PERSISTENT BROWSER WORKER


class BrowserWorker(QThread):

    status = Signal(str)
    command_completed = Signal()
    command_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.command_queue = queue.Queue()

        self.stop_requested = False

    
    # ADD COMMAND TO QUEUE
    

    def submit(
        self,
        action,
        site,
        query=None
    ):

        self.command_queue.put(
            {
                "action": action,
                "site": site,
                "query": query,
            }
        )

    
    # STOP WORKER
    

    def stop(self):

        self.stop_requested = True

        self.command_queue.put(
            {
                "action": "__stop__",
                "site": None,
                "query": None,
            }
        )

    
    # RUN
    

    def run(self):

        agent = BrowserAgent()

        try:

            while not self.stop_requested:

                command = self.command_queue.get()

                action = command["action"]

                if action == "__stop__":
                    break

                site = command["site"]

                query = command["query"]

                try:

        
                    # OPEN WEBSITE
        

                    if action == "open":

                        agent.open_site(
                            site=site,
                            status_callback=self.status.emit,
                        )

        
                    # SEARCH WEBSITE
        

                    elif action == "search":

                        agent.search_site(
                            site=site,
                            query=query,
                            status_callback=self.status.emit,
                        )

        
                    # CLOSE WEBSITE
        

                    elif action == "close":

                        agent.close_site(
                            site=site,
                            status_callback=self.status.emit,
                        )

                    else:

                        raise ValueError(
                            f"Unknown browser action: {action}"
                        )

                    self.command_completed.emit()

                except Exception as error:

                    self.command_failed.emit(
                        str(error)
                    )

        finally:

            agent.close()



# MAIN WINDOW


class DeskPilotWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "DeskPilot AI"
        )

        self.resize(
            920,
            660
        )

        self.setMinimumSize(
            800,
            580
        )

        # Default theme
        self.dark_mode = False

        # Build UI
        self.build_ui()

        self.apply_theme()

        
        # FILE AGENT
        

        self.file_agent = FileAgent()

        self.app_agent = AppAgent()

        self.planner = PlannerAgent()

        
        # PERSISTENT BROWSER WORKER
        

        self.browser_worker = BrowserWorker(
            self
        )

        self.browser_worker.status.connect(
            self.add_agent_message
        )

        self.browser_worker.command_completed.connect(
            self.browser_command_completed
        )

        self.browser_worker.command_failed.connect(
            self.browser_command_failed
        )

        self.browser_worker.start()

        self.tool_executor = ToolExecutor(
            file_agent=self.file_agent,
            app_agent=self.app_agent,
            browser_open_callback=self.open_site,
            browser_search_callback=self.search_site,
            browser_close_callback=self.close_site,
        )

        self.command_input.setFocus()

    
    # BUILD UI
    

    def build_ui(self):

        
        # CENTRAL WIDGET
        

        central_widget = QWidget()

        central_widget.setObjectName(
            "CentralWidget"
        )

        self.setCentralWidget(
            central_widget
        )

        main_layout = QVBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            35,
            30,
            35,
            25
        )

        main_layout.setSpacing(
            20
        )

        
        # HEADER
        

        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title_area.setContentsMargins(
            0,
            0,
            0,
            0
        )

        title_area.setSpacing(
            3
        )

        title = QLabel(
            "DeskPilot AI"
        )

        title.setObjectName(
            "Title"
        )

        subtitle = QLabel(
            "Your intelligent desktop automation assistant"
        )

        subtitle.setObjectName(
            "Subtitle"
        )

        title_area.addWidget(
            title
        )

        title_area.addWidget(
            subtitle
        )

        header.addLayout(
            title_area
        )

        header.addStretch()

        
        # HEADER CONTROLS
        

        controls = QHBoxLayout()

        controls.setSpacing(
            10
        )

        controls.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        # THEME BUTTON

        self.theme_button = QPushButton(
            "🌙  Dark Mode"
        )

        self.theme_button.setObjectName(
            "ThemeButton"
        )

        self.theme_button.setFixedHeight(
            36
        )

        self.theme_button.setMinimumWidth(
            130
        )

        self.theme_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        # STATUS

        self.status_label = QLabel(
            "●  Ready"
        )

        self.status_label.setObjectName(
            "StatusLabel"
        )

        self.status_label.setFixedHeight(
            36
        )

        self.status_label.setMinimumWidth(
            105
        )

        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        controls.addWidget(
            self.theme_button
        )

        controls.addWidget(
            self.status_label
        )

        header.addLayout(
            controls
        )

        main_layout.addLayout(
            header
        )

        
        # COMMAND CARD
        

        command_card = QFrame()

        command_card.setObjectName(
            "Card"
        )

        command_layout = QVBoxLayout(
            command_card
        )

        command_layout.setContentsMargins(
            24,
            22,
            24,
            22
        )

        command_layout.setSpacing(
            12
        )

        command_title = QLabel(
            "What would you like me to do?"
        )

        command_title.setObjectName(
            "SectionTitle"
        )

        description = QLabel(
            "Type an instruction and DeskPilot will execute it."
        )

        description.setObjectName(
            "Description"
        )

        # COMMAND INPUT

        self.command_input = QLineEdit()

        self.command_input.setObjectName(
            "CommandInput"
        )

        self.command_input.setPlaceholderText(
            "Try: Open YouTube and search..."
        )

        self.command_input.setMinimumHeight(
            52
        )

        # RUN BUTTON

        button_row = QHBoxLayout()

        button_row.addStretch()

        self.run_button = QPushButton(
            "▶  Run Agent"
        )

        self.run_button.setObjectName(
            "RunButton"
        )

        self.run_button.setMinimumHeight(
            46
        )

        self.run_button.setMinimumWidth(
            165
        )

        self.run_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button_row.addWidget(
            self.run_button
        )

        command_layout.addWidget(
            command_title
        )

        command_layout.addWidget(
            description
        )

        command_layout.addWidget(
            self.command_input
        )

        command_layout.addLayout(
            button_row
        )

        main_layout.addWidget(
            command_card
        )

        
        # ACTIVITY CARD
        

        activity_card = QFrame()

        activity_card.setObjectName(
            "Card"
        )

        activity_layout = QVBoxLayout(
            activity_card
        )

        activity_layout.setContentsMargins(
            24,
            20,
            24,
            22
        )

        activity_layout.setSpacing(
            12
        )

        activity_header = QHBoxLayout()

        activity_title = QLabel(
            "Agent Activity"
        )

        activity_title.setObjectName(
            "SectionTitle"
        )

        self.clear_button = QPushButton(
            "Clear"
        )

        self.clear_button.setObjectName(
            "ClearButton"
        )

        self.clear_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        activity_header.addWidget(
            activity_title
        )

        activity_header.addStretch()

        activity_header.addWidget(
            self.clear_button
        )

        # ACTIVITY LOG

        self.activity_log = QTextEdit()

        self.activity_log.setObjectName(
            "ActivityLog"
        )

        self.activity_log.setReadOnly(
            True
        )

        self.activity_log.setPlaceholderText(
            "DeskPilot activity will appear here..."
        )

        activity_layout.addLayout(
            activity_header
        )

        activity_layout.addWidget(
            self.activity_log
        )

        main_layout.addWidget(
            activity_card,
            1
        )

        
        # FOOTER
        

        footer = QLabel(
            "DeskPilot AI  •  Local Desktop Agent"
        )

        footer.setObjectName(
            "Footer"
        )

        footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        main_layout.addWidget(
            footer
        )

        
        # EVENTS
        

        self.run_button.clicked.connect(
            self.run_command
        )

        self.command_input.returnPressed.connect(
            self.run_command
        )

        self.clear_button.clicked.connect(
            self.activity_log.clear
        )

        self.theme_button.clicked.connect(
            self.toggle_theme
        )

    
    # RUN COMMAND
    

    def run_command(self):
        command = (
            self.command_input
            .text()
            .strip()
        )

        if not command:

            self.add_agent_message(
                "Please enter an instruction."
            )

            return

        # SHOW USER COMMAND

        self.add_user_message(
            command
        )

        self.command_input.clear()

        self.command_input.setFocus()

        self.status_label.setText(
            "●  Planning"
        )

        # =====================================================
        # STEP 1: ASK PLANNER TO UNDERSTAND USER LANGUAGE
        # =====================================================

        try:

            plan = self.planner.plan(
                command
            )

        except Exception as error:


            # GROQ / PLANNER FAILED
            # TRY OLD LOCAL PARSER AS FALLBACK


            try:

                handled = self.process_command(
                    command
                )

            except Exception as fallback_error:

                self.add_agent_message(
                    f"Planner error: {error}"
                )

                self.add_agent_message(
                    f"Fallback error: {fallback_error}"
                )

                self.set_status_ready()

                return

            if handled:

                return

            self.add_agent_message(
                f"I could not understand the command "
                f"because the AI planner is unavailable: "
                f"{error}"
            )

            self.set_status_ready()

            return

        # =====================================================
        # STEP 2: PLANNER COULD NOT MAP COMMAND
        # =====================================================

        if plan.get(
            "tool"
        ) == "unknown":

            # Try old parser before giving up
            try:

                handled = self.process_command(
                    command
                )

            except Exception as error:

                self.add_agent_message(
                    f"Command fallback failed: {error}"
                )

                self.set_status_ready()

                return

            if handled:

                return

            reason = (
                plan.get(
                    "args",
                    {}
                )
                .get(
                    "reason",
                    "I don't know how to perform that action yet."
                )
            )

            self.add_agent_message(
                reason
            )

            self.set_status_ready()

            return

        # =====================================================
        # STEP 3: EXECUTE PLANNER RESULT
        # =====================================================

        try:

            result = (
                self.tool_executor
                .execute(
                    plan
                )
            )

        except Exception as error:

            self.add_agent_message(
                f"Action failed: {error}"
            )

            self.set_status_ready()

            return

        # =====================================================
        # STEP 4: SHOW RESULT
        # =====================================================

        if isinstance(
            result,
            dict
        ):

            message = result.get(
                "message"
            )

            asynchronous = result.get(
                "asynchronous",
                False
            )

        else:

            message = str(
                result
            )

            asynchronous = False

        if message:

            self.add_agent_message(
                message
            )

        # Browser worker will set Ready when finished
        if not asynchronous:

            self.set_status_ready()

    
    # COMMAND PARSER
    

    def process_command(
        self,
        command
    ):

        original = command.strip()

        
        # FILE LOCATION NORMALIZER
        

        def normalize_location(
            location
        ):

            location = (
                location
                .lower()
                .strip()
            )

            aliases = {

                "download": "downloads",

                "downloads": "downloads",

                "document": "documents",

                "documents": "documents",

                "picture": "pictures",

                "pictures": "pictures",

                "desktop": "desktop",
            }

            return aliases.get(
                location,
                location
            )

        location_pattern = (
            r"desktop|"
            r"downloads?|"
            r"documents?|"
            r"pictures?"
        )

        
        # FILE EXPLORER → OPEN LOCATION
        

        # Examples:
        #
        # go to file explorer and search pictures folder
        # open file explorer and open downloads folder
        # go to file explorer and open documents

        match = re.match(

            rf"^(?:go\s+to|open)"

            rf"(?:\s+the)?\s+file\s+explorer"

            rf"\s+and\s+"

            rf"(?:search|open|go\s+to)"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            result = (
                self.file_agent
                .open_folder(
                    location
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # OPEN LOCAL FOLDER
        

        # Examples:
        #
        # open pictures
        # open the pictures folder
        # open downloads
        # go to documents folder

        match = re.match(

            rf"^(?:open|go\s+to)"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            result = (
                self.file_agent
                .open_folder(
                    location
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # LIST FILES
        

        # Examples:
        #
        # list files in downloads
        # show files in pictures
        # list all files in desktop
        # list files and folders in desktop

        match = re.match(

            rf"^(?:list|show)"

            rf"(?:\s+all)?\s+files"

            rf"(?:\s+and\s+folders)?"

            rf"\s+in"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            items = (
                self.file_agent
                .list_files(
                    location
                )
            )

            if not items:

                self.add_agent_message(
                    f"No files found in "
                    f"{location.title()}."
                )

            else:

                visible_items = (
                    items[:30]
                )

                lines = []

                for item in visible_items:

                    lines.append(
                        f"{item['type']}: "
                        f"{item['name']}"
                    )

                safe_lines = [
                    html.escape(line)
                    for line in lines
                ]

                result = (
                    "<br>".join(
                        safe_lines
                    )
                )

                if len(items) > 30:

                    result += (
                        f"<br>... and "
                        f"{len(items) - 30} more."
                    )

                self.add_agent_html(
                    f"<b>{html.escape(location.title())}</b>"
                    f"<br>{result}"
                )

            self.set_status_ready()

            return True

        
        # CREATE FOLDER
        

        # Examples:
        #
        # create folder ProjectX on desktop
        # create a folder Test in documents

        match = re.match(

            rf"^create"

            rf"(?:\s+a)?\s+folder\s+"

            rf"(?P<name>.+?)"

            rf"\s+(?:on|in)"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            folder_name = (
                match.group(
                    "name"
                )
                .strip()
            )

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            result = (
                self.file_agent
                .create_folder(
                    folder_name,
                    location
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # CREATE FILE
        

        # Examples:
        #
        # create file notes.txt on desktop
        # create a file test.txt in documents

        match = re.match(

            rf"^create"

            rf"(?:\s+a)?\s+file\s+"

            rf"(?P<name>.+?)"

            rf"\s+(?:on|in)"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            file_name = (
                match.group(
                    "name"
                )
                .strip()
            )

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            result = (
                self.file_agent
                .create_file(
                    file_name,
                    location
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # RENAME FILE / FOLDER
        

        # Example:
        #
        # rename notes.txt to ideas.txt on desktop

        match = re.match(

            rf"^rename\s+"

            rf"(?P<old>.+?)"

            rf"\s+to\s+"

            rf"(?P<new>.+?)"

            rf"\s+(?:on|in)"

            rf"(?:\s+the)?\s+"

            rf"(?P<location>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            old_name = (
                match.group(
                    "old"
                )
                .strip()
            )

            new_name = (
                match.group(
                    "new"
                )
                .strip()
            )

            location = normalize_location(
                match.group(
                    "location"
                )
            )

            result = (
                self.file_agent
                .rename_item(
                    old_name,
                    new_name,
                    location
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # COPY FILE / FOLDER
        

        # Example:
        #
        # copy notes.txt from desktop to documents

        match = re.match(

            rf"^copy\s+"

            rf"(?P<item>.+?)"

            rf"\s+from"

            rf"(?:\s+the)?\s+"

            rf"(?P<source>{location_pattern})"

            rf"(?:\s+folder)?"

            rf"\s+to"

            rf"(?:\s+the)?\s+"

            rf"(?P<destination>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            item_name = (
                match.group(
                    "item"
                )
                .strip()
            )

            source = normalize_location(
                match.group(
                    "source"
                )
            )

            destination = normalize_location(
                match.group(
                    "destination"
                )
            )

            result = (
                self.file_agent
                .copy_item(
                    item_name,
                    source,
                    destination
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # MOVE FILE / FOLDER
        

        # Example:
        #
        # move notes.txt from desktop to documents

        match = re.match(

            rf"^move\s+"

            rf"(?P<item>.+?)"

            rf"\s+from"

            rf"(?:\s+the)?\s+"

            rf"(?P<source>{location_pattern})"

            rf"(?:\s+folder)?"

            rf"\s+to"

            rf"(?:\s+the)?\s+"

            rf"(?P<destination>{location_pattern})"

            rf"(?:\s+folder)?$",

            original,

            re.IGNORECASE
        )

        if match:

            item_name = (
                match.group(
                    "item"
                )
                .strip()
            )

            source = normalize_location(
                match.group(
                    "source"
                )
            )

            destination = normalize_location(
                match.group(
                    "destination"
                )
            )

            result = (
                self.file_agent
                .move_item(
                    item_name,
                    source,
                    destination
                )
            )

            self.add_agent_message(
                result
            )

            self.set_status_ready()

            return True

        
        # BROWSER SITE CONFIG
        

        supported_sites = set(
            BrowserAgent
            .SITE_CONFIG
            .keys()
        )

        supported_sites.update(
            BrowserAgent
            .ALIASES
            .keys()
        )

        site_pattern = "|".join(

            re.escape(
                site
            )

            for site in sorted(
                supported_sites,
                key=len,
                reverse=True
            )
        )

        
        # CLOSE WEBSITE
        

        # Examples:
        #
        # close youtube
        # close the youtube
        # exit github
        # exit the bing

        match = re.match(

            rf"^(?:close|exit)\s+"

            rf"(?:the\s+)?"

            rf"(?P<site>{site_pattern})$",

            original,

            re.IGNORECASE
        )

        if match:

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            self.close_site(
                site
            )

            return True

        
        # OPEN WEBSITE AND SEARCH
        

        # Example:
        #
        # open youtube and search python for beginners

        match = re.match(

            rf"^(?:open\s+)?"

            rf"(?P<site>{site_pattern})"

            rf"\s+and\s+search"

            rf"(?:\s+for)?\s+"

            rf"(?P<query>.+)$",

            original,

            re.IGNORECASE
        )

        if match:

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            query = (
                match.group(
                    "query"
                )
                .strip()
            )

            self.search_site(
                site,
                query
            )

            return True

        
        # SEARCH QUERY IN / ON WEBSITE
        

        # Examples:
        #
        # search laravel for beginners in youtube
        # search python tutorial on youtube
        # search AI news in bing

        match = re.match(

            rf"^search"

            rf"(?:\s+for)?\s+"

            rf"(?P<query>.+?)"

            rf"\s+(?:in|on)\s+"

            rf"(?P<site>{site_pattern})$",

            original,

            re.IGNORECASE
        )

        if match:

            query = (
                match.group(
                    "query"
                )
                .strip()
            )

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            self.search_site(
                site,
                query
            )

            return True

        
        # SEARCH WEBSITE FOR QUERY
        

        # Examples:
        #
        # search github for playwright
        # search youtube for laravel tutorial
        # search google for python jobs

        match = re.match(

            rf"^search\s+"

            rf"(?P<site>{site_pattern})"

            rf"\s+for\s+"

            rf"(?P<query>.+)$",

            original,

            re.IGNORECASE
        )

        if match:

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            query = (
                match.group(
                    "query"
                )
                .strip()
            )

            self.search_site(
                site,
                query
            )

            return True

        
        # WEBSITE SEARCH QUERY
        

        # Examples:
        #
        # youtube search laravel tutorial
        # github search playwright
        # bing search AI news

        match = re.match(

            rf"^(?P<site>{site_pattern})"

            rf"\s+search"

            rf"(?:\s+for)?\s+"

            rf"(?P<query>.+)$",

            original,

            re.IGNORECASE
        )

        if match:

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            query = (
                match.group(
                    "query"
                )
                .strip()
            )

            self.search_site(
                site,
                query
            )

            return True

        
        # OPEN WEBSITE
        

        # Examples:
        #
        # open youtube
        # open the youtube
        # launch github
        # go to wikipedia

        match = re.match(

            rf"^(?:open|launch|go\s+to)"

            rf"(?:\s+the)?\s+"

            rf"(?P<site>{site_pattern})$",

            original,

            re.IGNORECASE
        )

        if match:

            site = (
                match.group(
                    "site"
                )
                .lower()
                .strip()
            )

            self.open_site(
                site
            )

            return True
        

        return False

    
    # BROWSER COMMAND DISPATCH
    

    def open_site(
        self,
        site
    ):

        self.set_status_browser()

        self.browser_worker.submit(
            action="open",
            site=site,
        )

    def search_site(
        self,
        site,
        query
    ):

        self.set_status_browser()

        self.browser_worker.submit(
            action="search",
            site=site,
            query=query,
        )

    def close_site(
        self,
        site
    ):

        self.set_status_browser()

        self.browser_worker.submit(
            action="close",
            site=site,
        )

    
    # BROWSER CALLBACKS
    

    def browser_command_completed(self):

        self.set_status_ready()

    def browser_command_failed(
        self,
        error
    ):

        self.add_agent_message(
            f"Browser automation error: {error}"
        )

        self.set_status_ready()

    
    # ACTIVITY LOG
    

    def add_user_message(
        self,
        message
    ):

        safe_message = html.escape(
            message
        )

        self.activity_log.append(
            f"""
            <div style="
                margin-top:8px;
                margin-bottom:14px;
            ">
                <b>You</b>
                <br>
                {safe_message}
            </div>
            """
        )

    def add_agent_message(
        self,
        message
    ):

        safe_message = html.escape(
            message
        )

        self.activity_log.append(
            f"""
            <div style="
                margin-top:8px;
                margin-bottom:14px;
            ">
                <b>DeskPilot</b>
                <br>
                {safe_message}
            </div>
            """
        )

    def add_agent_html(
        self,
        content
    ):

        self.activity_log.append(
            f"""
            <div style="
                margin-top:8px;
                margin-bottom:14px;
            ">
                <b>DeskPilot</b>
                <br>
                {content}
            </div>
            """
        )

    
    # STATUS
    

    def set_status_ready(self):

        self.status_label.setText(
            "●  Ready"
        )

    def set_status_browser(self):

        self.status_label.setText(
            "●  Browser"
        )

    
    # THEME
    

    def toggle_theme(self):

        self.dark_mode = (
            not self.dark_mode
        )

        if self.dark_mode:

            self.theme_button.setText(
                "🌸  Pink Mode"
            )

        else:

            self.theme_button.setText(
                "🌙  Dark Mode"
            )

        self.apply_theme()

    def apply_theme(self):

        if self.dark_mode:

            self.apply_dark_theme()

        else:

            self.apply_pink_theme()

    
    # PINK THEME
    

    def apply_pink_theme(self):

        self.setStyleSheet(
            """

            QMainWindow,
            QWidget#CentralWidget {
                background: #fff7fb;
            }

            QWidget {
                font-family: "Segoe UI";
                font-size: 14px;
                color: #3f2935;
            }

            QLabel#Title {
                font-size: 31px;
                font-weight: 700;
                color: #9d174d;
            }

            QLabel#Subtitle {
                font-size: 14px;
                color: #8c6377;
            }

            QLabel#StatusLabel {
                background: #ecfdf3;
                color: #15803d;

                border:
                    1px solid #bbf7d0;

                border-radius: 12px;

                padding-left: 12px;
                padding-right: 12px;

                font-weight: 600;
            }

            QFrame#Card {
                background: #ffffff;

                border:
                    1px solid #f3c8da;

                border-radius: 17px;
            }

            QLabel#SectionTitle {
                font-size: 17px;

                font-weight: 650;

                color: #4a2639;
            }

            QLabel#Description {
                color: #987184;

                font-size: 13px;
            }

            QLineEdit#CommandInput {
                background: #fffafd;

                color: #3f2935;

                border:
                    1px solid #edbfd3;

                border-radius: 11px;

                padding-left: 16px;
                padding-right: 16px;

                font-size: 14px;
            }

            QLineEdit#CommandInput:hover {
                border:
                    1px solid #e88bb5;
            }

            QLineEdit#CommandInput:focus {
                border:
                    2px solid #db2777;
            }

            QPushButton#RunButton {
                background: #db2777;

                color: white;

                border: none;

                border-radius: 10px;

                padding:
                    10px 22px;

                font-size: 14px;

                font-weight: 650;
            }

            QPushButton#RunButton:hover {
                background: #be185d;
            }

            QPushButton#RunButton:pressed {
                background: #9d174d;
            }

            QPushButton#ThemeButton {
                background: #ffffff;

                color: #9d174d;

                border:
                    1px solid #f3c8da;

                border-radius: 10px;

                padding-left: 14px;
                padding-right: 14px;

                font-weight: 600;
            }

            QPushButton#ThemeButton:hover {
                background: #fdf2f8;
            }

            QPushButton#ClearButton {
                background: #fff7fb;

                color: #9d174d;

                border:
                    1px solid #f3c8da;

                border-radius: 7px;

                padding:
                    6px 14px;
            }

            QPushButton#ClearButton:hover {
                background: #fce7f3;
            }

            QTextEdit#ActivityLog {
                background: #fffafd;

                border:
                    1px solid #f0d1df;

                border-radius: 11px;

                padding: 14px;

                color: #4a2639;

                font-size: 14px;
            }

            QLabel#Footer {
                color: #ae8799;

                font-size: 12px;
            }

            """
        )

    
    # DARK THEME
    

    def apply_dark_theme(self):

        self.setStyleSheet(
            """

            QMainWindow,
            QWidget#CentralWidget {
                background: #090d18;
            }

            QWidget {
                font-family: "Segoe UI";

                font-size: 14px;

                color: #e5e7eb;
            }

            QLabel#Title {
                font-size: 31px;

                font-weight: 700;

                color: #ffffff;
            }

            QLabel#Subtitle {
                font-size: 14px;

                color: #8b93a7;
            }

            QLabel#StatusLabel {
                background: #10251a;

                color: #4ade80;

                border:
                    1px solid #245b39;

                border-radius: 12px;

                padding-left: 12px;
                padding-right: 12px;

                font-weight: 600;
            }

            QFrame#Card {
                background: #111827;

                border:
                    1px solid #222c3e;

                border-radius: 17px;
            }

            QLabel#SectionTitle {
                font-size: 17px;

                font-weight: 650;

                color: #f9fafb;
            }

            QLabel#Description {
                color: #8b93a7;

                font-size: 13px;
            }

            QLineEdit#CommandInput {
                background: #0b1220;

                color: #f8fafc;

                border:
                    1px solid #29354b;

                border-radius: 11px;

                padding-left: 16px;
                padding-right: 16px;

                font-size: 14px;
            }

            QLineEdit#CommandInput:hover {
                border:
                    1px solid #475569;
            }

            QLineEdit#CommandInput:focus {
                border:
                    2px solid #8b5cf6;
            }

            QPushButton#RunButton {
                background: #7c3aed;

                color: white;

                border: none;

                border-radius: 10px;

                padding:
                    10px 22px;

                font-size: 14px;

                font-weight: 650;
            }

            QPushButton#RunButton:hover {
                background: #8b5cf6;
            }

            QPushButton#RunButton:pressed {
                background: #6d28d9;
            }

            QPushButton#ThemeButton {
                background: #111827;

                color: #c4b5fd;

                border:
                    1px solid #303b50;

                border-radius: 10px;

                padding-left: 14px;
                padding-right: 14px;

                font-weight: 600;
            }

            QPushButton#ThemeButton:hover {
                background: #182235;
            }

            QPushButton#ClearButton {
                background: transparent;

                color: #9ca3af;

                border:
                    1px solid #303b50;

                border-radius: 7px;

                padding:
                    6px 14px;
            }

            QPushButton#ClearButton:hover {
                background: #1a2334;

                color: #ffffff;
            }

            QTextEdit#ActivityLog {
                background: #0b1220;

                border:
                    1px solid #222c3e;

                border-radius: 11px;

                padding: 14px;

                color: #dbeafe;

                font-size: 14px;
            }

            QLabel#Footer {
                color: #596174;

                font-size: 12px;
            }

            """
        )

    
    # CLOSE DESKPILOT
    

    def closeEvent(
        self,
        event
    ):

        self.browser_worker.stop()

        self.browser_worker.wait(
            5000
        )

        event.accept()



# START APPLICATION


if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    app.setStyle(
        "Fusion"
    )

    window = DeskPilotWindow()

    window.show()

    sys.exit(
        app.exec()
    )