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

            if self.browser is None:
                return False

            if not self.browser.is_connected():
                return False

            if self.context is None:
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
    # START / REUSE CHROMIUM
    # =========================================================

    def ensure_browser(
        self,
        status_callback=None
    ):

        def status(message):

            if status_callback:
                status_callback(message)

        # Reuse existing healthy browser
        if self.session_is_usable():
            return

        # Remove stale/dead references
        self.close()

        status(
            "Opening Chromium..."
        )

        self.playwright = (
            sync_playwright()
            .start()
        )

        self.browser = (
            self.playwright
            .chromium
            .launch(
                headless=False
            )
        )

        self.context = (
            self.browser
            .new_context(
                viewport={
                    "width": 1280,
                    "height": 800,
                }
            )
        )

        self.page = (
            self.context
            .new_page()
        )

        status(
            "Chromium ready."
        )

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

        # PAGE
        try:

            if (
                self.page is not None
                and not self.page.is_closed()
            ):

                self.page.close()

        except Exception:
            pass

        # CONTEXT
        try:

            if self.context is not None:

                self.context.close()

        except Exception:
            pass

        # BROWSER
        try:

            if (
                self.browser is not None
                and self.browser.is_connected()
            ):

                self.browser.close()

        except Exception:
            pass

        # PLAYWRIGHT
        try:

            if self.playwright is not None:

                self.playwright.stop()

        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None