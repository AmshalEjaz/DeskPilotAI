import sys
import re
import webbrowser
import html
from urllib.parse import quote_plus

from PySide6.QtCore import Qt
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


class DeskPilotWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("DeskPilot AI")
        self.resize(920, 660)
        self.setMinimumSize(800, 580)

        # Default theme = Pink
        self.dark_mode = False

        self.build_ui()
        self.apply_theme()

    
    # BUILD UI
    

    def build_ui(self):

        # -----------------------------------------------------
        # MAIN WINDOW
        # -----------------------------------------------------

        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")

        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)

        main_layout.setContentsMargins(
            35,
            30,
            35,
            25
        )

        main_layout.setSpacing(20)

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        header_layout = QHBoxLayout()

        header_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        header_layout.setSpacing(10)

        # LEFT SIDE
        title_area = QVBoxLayout()

        title_area.setContentsMargins(
            0,
            0,
            0,
            0
        )

        title_area.setSpacing(3)

        title = QLabel("DeskPilot AI")

        title.setObjectName("Title")

        subtitle = QLabel(
            "Your intelligent desktop automation assistant"
        )

        subtitle.setObjectName("Subtitle")

        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        header_layout.addLayout(title_area)

        header_layout.addStretch()

        # RIGHT SIDE
        right_controls = QHBoxLayout()

        right_controls.setContentsMargins(
            0,
            0,
            0,
            0
        )

        right_controls.setSpacing(10)

        # THEME BUTTON
        self.theme_button = QPushButton(
            "🌙  Dark Mode"
        )

        self.theme_button.setObjectName(
            "ThemeButton"
        )

        self.theme_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.theme_button.setFixedHeight(36)

        self.theme_button.setMinimumWidth(130)

        # STATUS
        self.status_label = QLabel(
            "●  Ready"
        )

        self.status_label.setObjectName(
            "StatusLabel"
        )

        self.status_label.setFixedHeight(36)

        self.status_label.setMinimumWidth(90)

        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        right_controls.addWidget(
            self.theme_button
        )

        right_controls.addWidget(
            self.status_label
        )

        # Keeps both controls at top
        right_controls.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        header_layout.addLayout(
            right_controls
        )

        main_layout.addLayout(
            header_layout
        )

        # -----------------------------------------------------
        # COMMAND CARD
        # -----------------------------------------------------

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

        command_layout.setSpacing(12)

        command_title = QLabel(
            "What would you like me to do?"
        )

        command_title.setObjectName(
            "SectionTitle"
        )

        command_description = QLabel(
            "Type an instruction and DeskPilot will execute it."
        )

        command_description.setObjectName(
            "Description"
        )

        # COMMAND INPUT
        self.command_input = QLineEdit()

        self.command_input.setObjectName(
            "CommandInput"
        )

        self.command_input.setPlaceholderText(
            "Try: Open Google and search Python jobs"
        )

        self.command_input.setMinimumHeight(
            52
        )

        # RUN BUTTON ROW
        button_row = QHBoxLayout()

        button_row.addStretch()

        self.run_button = QPushButton(
            "▶  Run Agent"
        )

        self.run_button.setObjectName(
            "RunButton"
        )

        self.run_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.run_button.setMinimumHeight(
            46
        )

        self.run_button.setMinimumWidth(
            165
        )

        button_row.addWidget(
            self.run_button
        )

        command_layout.addWidget(
            command_title
        )

        command_layout.addWidget(
            command_description
        )

        command_layout.addSpacing(5)

        command_layout.addWidget(
            self.command_input
        )

        command_layout.addSpacing(5)

        command_layout.addLayout(
            button_row
        )

        main_layout.addWidget(
            command_card
        )

        # -----------------------------------------------------
        # ACTIVITY CARD
        # -----------------------------------------------------

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

        activity_layout.setSpacing(12)

        activity_header = QHBoxLayout()

        activity_title = QLabel(
            "Agent Activity"
        )

        activity_title.setObjectName(
            "SectionTitle"
        )

        # CLEAR BUTTON
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

        # LOG
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

        # -----------------------------------------------------
        # FOOTER
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # EVENTS
        # -----------------------------------------------------

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

       # =========================================================
    # RUN COMMAND
    # =========================================================

    def run_command(self):
        command = self.command_input.text().strip()

        if not command:
            self.add_agent_message(
                "Please enter an instruction first."
            )
            return

        self.set_status_working()

        # Show user's command in activity log
        self.add_user_message(command)

        # Clear input after command is submitted
        self.command_input.clear()

        # Put cursor back in input
        self.command_input.setFocus()

        try:
            handled = self.process_command(command)

            if not handled:
                self.add_agent_message(
                    "I don't know how to perform that action yet."
                )

        except Exception as error:
            self.add_agent_message(
                f"Something went wrong: {error}"
            )

        self.set_status_ready()
    # PROCESS COMMAND
    

    def process_command(
        self,
        command
    ):

        command_lower = (
            command
            .lower()
            .strip()
        )

        # -----------------------------------------------------
        # GOOGLE SEARCH PATTERNS
        # -----------------------------------------------------

        search_patterns = [

            r"open google and search(?: for)? (.+)",

            r"google and search(?: for)? (.+)",

            r"search google for (.+)",

            r"search for (.+) on google",

            r"google search(?: for)? (.+)",

        ]

        for pattern in search_patterns:

            match = re.search(
                pattern,
                command_lower,
                re.IGNORECASE
            )

            if match:

                search_query = (
                    match
                    .group(1)
                    .strip()
                )

                self.google_search(
                    search_query
                )

                return True

        # -----------------------------------------------------
        # OPEN GOOGLE
        # -----------------------------------------------------

        google_commands = [

            "open google",

            "launch google",

            "go to google",

        ]

        if command_lower in google_commands:

            self.open_google()

            return True

        return False

    
    # GOOGLE FUNCTIONS
    

    def open_google(self):

        self.add_agent_message(
            "Opening Google..."
        )

        webbrowser.open(
            "https://www.google.com"
        )

        self.add_agent_message(
            "Google opened successfully."
        )

    def google_search(
        self,
        search_query
    ):

        self.add_agent_message(
            f"Searching Google for: {search_query}"
        )

        encoded_query = quote_plus(
            search_query
        )

        search_url = (
            "https://www.google.com/search?q="
            + encoded_query
        )

        webbrowser.open(
            search_url
        )

        self.add_agent_message(
            "Search opened successfully in your browser."
        )

    
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

                <span style="
                    font-size:14px;
                    font-weight:600;
                ">
                    You
                </span>

                <br>

                <span>
                    {safe_message}
                </span>

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

                <span style="
                    font-size:14px;
                    font-weight:600;
                ">
                    DeskPilot
                </span>

                <br>

                <span>
                    {safe_message}
                </span>

            </div>
            """
        )

    
    # STATUS
    

    def set_status_ready(self):

        self.status_label.setText(
            "●  Ready"
        )

    def set_status_working(self):

        self.status_label.setText(
            "●  Working"
        )

    
    # THEME SWITCH
    

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

    
    # APPLY THEME
    

    def apply_theme(self):

        if self.dark_mode:

            self.apply_dark_theme()

        else:

            self.apply_pink_theme()

    
    # PINK THEME
    

    def apply_pink_theme(self):

        self.setStyleSheet(
            """

            QMainWindow {
                background-color: #fff7fb;
            }

            QWidget#CentralWidget {
                background-color: #fff7fb;
            }

            QWidget {
                font-family: "Segoe UI";
                font-size: 14px;
                color: #3f2935;
            }


            /* TITLE */

            QLabel#Title {
                font-size: 31px;
                font-weight: 700;
                color: #9d174d;
            }


            QLabel#Subtitle {
                font-size: 14px;
                color: #8c6377;
            }


            /* STATUS */

            QLabel#StatusLabel {

                background-color: #ecfdf3;

                color: #15803d;

                border: 1px solid #bbf7d0;

                border-radius: 12px;

                padding-left: 12px;

                padding-right: 12px;

                font-weight: 600;
            }


            /* CARDS */

            QFrame#Card {

                background-color: #ffffff;

                border: 1px solid #f3c8da;

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


            /* INPUT */

            QLineEdit#CommandInput {

                background-color: #fffafd;

                color: #3f2935;

                border: 1px solid #edbfd3;

                border-radius: 11px;

                padding-left: 16px;

                padding-right: 16px;

                font-size: 14px;

                selection-background-color: #f472b6;
            }


            QLineEdit#CommandInput:hover {

                border: 1px solid #e88bb5;
            }


            QLineEdit#CommandInput:focus {

                border: 2px solid #db2777;
            }


            /* RUN BUTTON */

            QPushButton#RunButton {

                background-color: #db2777;

                color: white;

                border: none;

                border-radius: 10px;

                padding: 10px 22px;

                font-size: 14px;

                font-weight: 650;
            }


            QPushButton#RunButton:hover {

                background-color: #be185d;
            }


            QPushButton#RunButton:pressed {

                background-color: #9d174d;
            }


            /* THEME BUTTON */

            QPushButton#ThemeButton {

                background-color: #ffffff;

                color: #9d174d;

                border: 1px solid #f3c8da;

                border-radius: 10px;

                padding-left: 14px;

                padding-right: 14px;

                font-weight: 600;
            }


            QPushButton#ThemeButton:hover {

                background-color: #fdf2f8;
            }


            /* CLEAR */

            QPushButton#ClearButton {

                background-color: #fff7fb;

                color: #9d174d;

                border: 1px solid #f3c8da;

                border-radius: 7px;

                padding: 6px 14px;
            }


            QPushButton#ClearButton:hover {

                background-color: #fce7f3;
            }


            /* ACTIVITY */

            QTextEdit#ActivityLog {

                background-color: #fffafd;

                border: 1px solid #f0d1df;

                border-radius: 11px;

                padding: 14px;

                color: #4a2639;

                font-size: 14px;
            }


            QTextEdit#ActivityLog:focus {

                border: 1px solid #e88bb5;
            }


            /* SCROLLBAR */

            QScrollBar:vertical {

                border: none;

                background: #fff7fb;

                width: 9px;

                margin: 4px;
            }


            QScrollBar::handle:vertical {

                background: #e6afc7;

                border-radius: 4px;

                min-height: 30px;
            }


            QScrollBar::handle:vertical:hover {

                background: #d984aa;
            }


            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {

                height: 0px;
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

            QMainWindow {

                background-color: #090d18;
            }


            QWidget#CentralWidget {

                background-color: #090d18;
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


            /* STATUS */

            QLabel#StatusLabel {

                background-color: #10251a;

                color: #4ade80;

                border: 1px solid #245b39;

                border-radius: 12px;

                padding-left: 12px;

                padding-right: 12px;

                font-weight: 600;
            }


            /* CARD */

            QFrame#Card {

                background-color: #111827;

                border: 1px solid #222c3e;

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


            /* INPUT */

            QLineEdit#CommandInput {

                background-color: #0b1220;

                color: #f8fafc;

                border: 1px solid #29354b;

                border-radius: 11px;

                padding-left: 16px;

                padding-right: 16px;

                font-size: 14px;

                selection-background-color: #7c3aed;
            }


            QLineEdit#CommandInput:hover {

                border: 1px solid #475569;
            }


            QLineEdit#CommandInput:focus {

                border: 2px solid #8b5cf6;
            }


            /* RUN */

            QPushButton#RunButton {

                background-color: #7c3aed;

                color: white;

                border: none;

                border-radius: 10px;

                padding: 10px 22px;

                font-size: 14px;

                font-weight: 650;
            }


            QPushButton#RunButton:hover {

                background-color: #8b5cf6;
            }


            QPushButton#RunButton:pressed {

                background-color: #6d28d9;
            }


            /* THEME */

            QPushButton#ThemeButton {

                background-color: #111827;

                color: #c4b5fd;

                border: 1px solid #303b50;

                border-radius: 10px;

                padding-left: 14px;

                padding-right: 14px;

                font-weight: 600;
            }


            QPushButton#ThemeButton:hover {

                background-color: #182235;
            }


            /* CLEAR */

            QPushButton#ClearButton {

                background-color: transparent;

                color: #9ca3af;

                border: 1px solid #303b50;

                border-radius: 7px;

                padding: 6px 14px;
            }


            QPushButton#ClearButton:hover {

                background-color: #1a2334;

                color: #ffffff;
            }


            /* ACTIVITY */

            QTextEdit#ActivityLog {

                background-color: #0b1220;

                border: 1px solid #222c3e;

                border-radius: 11px;

                padding: 14px;

                color: #dbeafe;

                font-size: 14px;
            }


            QTextEdit#ActivityLog:focus {

                border: 1px solid #374151;
            }


            /* SCROLLBAR */

            QScrollBar:vertical {

                border: none;

                background: #0b1220;

                width: 9px;

                margin: 4px;
            }


            QScrollBar::handle:vertical {

                background: #374151;

                border-radius: 4px;

                min-height: 30px;
            }


            QScrollBar::handle:vertical:hover {

                background: #4b5563;
            }


            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {

                height: 0px;
            }


            QLabel#Footer {

                color: #596174;

                font-size: 12px;
            }

            """
        )



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