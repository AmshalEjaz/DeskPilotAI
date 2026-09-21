class DeskPilotWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("DeskPilot AI")
        self.resize(920, 660)
        self.setMinimumSize(800, 580)

        self.dark_mode = False

        self.browser_agent = BrowserAgent()

        self.build_ui()
        self.apply_theme()