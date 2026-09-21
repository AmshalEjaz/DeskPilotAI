from playwright.sync_api import sync_playwright


class BrowserAgent:

    def google_search(self, query):

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False
            )

            page = browser.new_page(
                viewport={
                    "width": 1280,
                    "height": 800
                }
            )

            page.goto(
                "https://www.google.com",
                wait_until="domcontentloaded"
            )

            search_box = page.locator(
                'textarea[name="q"]'
            )

            search_box.fill(query)

            search_box.press("Enter")

            page.wait_for_load_state(
                "domcontentloaded"
            )

            print(
                f"Search completed: {query}"
            )

            input(
                "Press Enter in terminal to close browser..."
            )

            browser.close()