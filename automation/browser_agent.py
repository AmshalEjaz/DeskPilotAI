from urllib.parse import quote_plus

from playwright.sync_api import (
    Error as PlaywrightError,
    sync_playwright,
)


class BrowserAgent:

    SITE_CONFIG = {
        "google": {
            "home": "https://www.google.com",
            "search": "https://www.google.com/search?q={query}",
        },

        "youtube": {
            "home": "https://www.youtube.com",
            "search": "https://www.youtube.com/results?search_query={query}",
        },

        "github": {
            "home": "https://github.com",
            "search": "https://github.com/search?q={query}",
        },

        "bing": {
            "home": "https://www.bing.com",
            "search": "https://www.bing.com/search?q={query}",
        },

        "wikipedia": {
            "home": "https://www.wikipedia.org",
            "search": (
                "https://en.wikipedia.org/wiki/"
                "Special:Search?search={query}"
            ),
        },

        "duckduckgo": {
            "home": "https://duckduckgo.com",
            "search": "https://duckduckgo.com/?q={query}",
        },
    }

    ALIASES = {
        "yt": "youtube",
        "wiki": "wikipedia",
        "ddg": "duckduckgo",
    }

    SITE_DOMAINS = {
        "google": "google.",
        "youtube": "youtube.com",
        "github": "github.com",
        "bing": "bing.com",
        "wikipedia": "wikipedia.org",
        "duckduckgo": "duckduckgo.com",
    }

    def __init__(self):

        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.chrome_process = None
        self.chrome_port = None

    # =========================================================
    # SITE CONFIG
    # =========================================================

    def get_site_config(self, site):

        site = site.lower().strip()

        site = self.ALIASES.get(
            site,
            site
        )

        config = self.SITE_CONFIG.get(
            site
        )

        if config is None:

            supported = ", ".join(
                self.SITE_CONFIG.keys()
            )

            raise ValueError(
                f"{site} is not supported yet. "
                f"Supported sites: {supported}"
            )

        return site, config

    # =========================================================
    # CHECK CURRENT SESSION
    # =========================================================

    def session_is_usable(self):

        try:

            if self.playwright is None:
                return False

            if self.context is None:
                return False

            # launch_persistent_context returns the live browser context;
            # there is no separate Browser object to check.
            if self.context.pages is None:
                return False

            if self.page is None:
                return False

            if self.page.is_closed():
                return False

            # Verify page is really alive
            self.page.evaluate("1")

            return True

        except Exception:

            return False

    # =========================================================
    # START / REUSE CHROME
    # =========================================================

    def ensure_browser(
        self,
        status_callback=None
    ):

        def status(message):
            if status_callback:
                status_callback(message)

        if self.session_is_usable():
            return

        self.close()

        status("Opening Google Chrome...")

        self.playwright = sync_playwright().start()

        import os
        import socket
        import subprocess
        import time
        from pathlib import Path

        # IMPORTANT:
        # Do NOT use Playwright's launch()/launch_persistent_context() for
        # YouTube here. Playwright adds automation-specific browser startup
        # arguments, and YouTube playback is sensitive to browser/runtime
        # differences. Instead, start the installed Chrome executable as a
        # normal Chrome process with a dedicated profile, then attach to it
        # through Chrome DevTools Protocol (CDP).
        #
        # This gives DeskPilot a real Chrome window while keeping the user's
        # normal Chrome profile completely separate.
        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            os.path.join(os.path.expanduser("~"), "AppData", "Local")
        )

        chrome_candidates = [
            os.path.join(
                local_app_data, "Google", "Chrome", "Application", "chrome.exe"
            ),
            os.path.join(
                os.environ.get("PROGRAMFILES", r"C:\\Program Files"),
                "Google", "Chrome", "Application", "chrome.exe"
            ),
            os.path.join(
                os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)"),
                "Google", "Chrome", "Application", "chrome.exe"
            ),
        ]

        chrome_path = next(
            (candidate for candidate in chrome_candidates if os.path.exists(candidate)),
            None,
        )

        if chrome_path is None:
            raise RuntimeError(
                "Google Chrome was not found. Install Google Chrome and try again."
            )

        # Pick a free localhost port instead of assuming 9222 is available.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        profile_dir = os.path.join(
            local_app_data,
            "DeskPilotAI",
            "ChromeCDPProfile",
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        command = [
            chrome_path,
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
        ]

        try:
            self.chrome_process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not start Google Chrome: {exc}"
            ) from exc

        self.chrome_port = port

        # Wait for Chrome's DevTools endpoint to become available.
        endpoint = f"http://127.0.0.1:{port}"
        last_error = None

        for _ in range(60):
            try:
                self.browser = self.playwright.chromium.connect_over_cdp(endpoint)
                break
            except Exception as exc:
                last_error = exc
                time.sleep(0.25)
        else:
            self.close()
            raise RuntimeError(
                f"Could not connect to Google Chrome through CDP: {last_error}"
            )

        contexts = self.browser.contexts
        if not contexts:
            self.close()
            raise RuntimeError("Chrome started, but no browser context was available.")

        self.context = contexts[0]
        pages = list(self.context.pages)
        self.page = pages[0] if pages else self.context.new_page()

        status("Google Chrome ready.")

    # =========================================================
    # NAVIGATION WITH AUTO RECOVERY
    # =========================================================

    def navigate(
        self,
        url,
        status_callback=None
    ):

        def status(message):

            if status_callback:
                status_callback(message)

        # Attempt 1 = reuse current browser
        # Attempt 2 = recreate browser if old session died
        for attempt in range(2):

            self.ensure_browser(
                status_callback
            )

            try:

                self.page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                try:
                    self.page.bring_to_front()
                except Exception:
                    pass

                return

            except PlaywrightError as error:

                error_text = str(error).lower()

                browser_closed_error = (
                    "target page" in error_text
                    or
                    "browser has been closed" in error_text
                    or
                    "context or browser has been closed" in error_text
                    or
                    "page has been closed" in error_text
                )

                if (
                    attempt == 0
                    and browser_closed_error
                ):

                    status(
                        "Previous browser session was closed. "
                        "Reopening Chromium..."
                    )

                    self.close()

                    continue

                raise

    # =========================================================
    # OPEN WEBSITE
    # =========================================================

    def open_site(
        self,
        site,
        status_callback=None
    ):

        def status(message):

            if status_callback:
                status_callback(message)

        site, config = (
            self.get_site_config(site)
        )

        status(
            f"Opening {site.title()}..."
        )

        self.navigate(
            config["home"],
            status_callback
        )

        status(
            f"{site.title()} opened successfully."
        )

    # =========================================================
    # SEARCH WEBSITE
    # =========================================================

    def search_site(
        self,
        site,
        query,
        status_callback=None
    ):

        def status(message):

            if status_callback:
                status_callback(message)

        site, config = (
            self.get_site_config(site)
        )

        query = query.strip()

        if not query:

            raise ValueError(
                "Search query cannot be empty."
            )

        encoded_query = quote_plus(
            query
        )

        search_url = (
            config["search"]
            .format(
                query=encoded_query
            )
        )

        status(
            f"Searching {site.title()} "
            f"for: {query}"
        )

        self.navigate(
            search_url,
            status_callback
        )

        status(
            f"Search completed on "
            f"{site.title()}."
        )

        if site == "google":

            status(
                "If Google asks for human "
                "verification, complete it "
                "manually in Chromium."
            )

    # =========================================================
    # CLOSE WEBSITE
    # =========================================================

    def close_site(
        self,
        site,
        status_callback=None
    ):

        def status(message):
            if status_callback:
                status_callback(message)

        site, _ = self.get_site_config(site)

        if not self.session_is_usable():
            status(f"{site.title()} is not currently open.")
            return

        current_url = self.page.url.lower()
        expected_domain = self.SITE_DOMAINS.get(site)

        if expected_domain and expected_domain not in current_url:
            status(f"{site.title()} is not the currently active website.")
            return

        status(f"Closing {site.title()}...")

        # The browser is a dedicated automation window. Closing only the
        # Playwright page leaves a blank Chromium tab behind. Close the
        # whole browser session instead so the user sees the window actually
        # disappear. The next browser command will create a fresh session.
        self.close()

        status(f"{site.title()} closed successfully.")

    # =========================================================
    # CLEANUP COMPLETE BROWSER
    # =========================================================

    def close(self):
        context = self.context
        page = self.page
        browser = self.browser
        playwright = self.playwright
        chrome_process = self.chrome_process

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.chrome_process = None
        self.chrome_port = None

        # CDP browser.close() disconnects Playwright from Chrome. The Chrome
        # process itself is then terminated explicitly so DeskPilot does not
        # leave an orphaned blank browser window behind.
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass

        try:
            if context is not None:
                context.close()
        except Exception:
            pass

        try:
            if page is not None and not page.is_closed():
                page.close()
        except Exception:
            pass

        try:
            if playwright is not None:
                playwright.stop()
        except Exception:
            pass

        try:
            if chrome_process is not None and chrome_process.poll() is None:
                chrome_process.terminate()
                chrome_process.wait(timeout=3)
        except Exception:
            try:
                if chrome_process is not None and chrome_process.poll() is None:
                    chrome_process.kill()
            except Exception:
                pass

