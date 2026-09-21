from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page()

        print("Opening Google...")

        page.goto(
            "https://www.google.com",
            wait_until="domcontentloaded"
        )

        print("Google opened.")

        page.locator('textarea[name="q"]').fill(
            "Python jobs"
        )

        page.locator('textarea[name="q"]').press(
            "Enter"
        )

        page.wait_for_load_state(
            "domcontentloaded"
        )

        print("Search completed.")
        print("Page title:", page.title())

        input(
            "\nPress Enter in terminal to close browser..."
        )

        browser.close()


if __name__ == "__main__":
    main()