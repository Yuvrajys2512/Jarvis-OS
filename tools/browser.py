import re
from playwright.sync_api import sync_playwright, Page


def open_url(url: str) -> str:
    """Open a URL in a visible browser window and leave it open."""
    import subprocess
    subprocess.Popen(f'start "" "{url}"', shell=True)
    return f"Opened {url} in your browser."


def search_google(query: str) -> str:
    """
    Open Google in a visible browser and search for the query.
    Leaves the browser open so the user can see results.
    """
    import subprocess
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    subprocess.Popen(f'start "" "{search_url}"', shell=True)
    return f"Searched Google for: {query}"


def get_page_text(url: str) -> str:
    """
    Fetch the visible text content of a webpage using a headless browser.
    Used for reading articles, docs, or product pages.
    Returns the first 3000 characters to stay within context limits.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            text = page.inner_text("body")
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            return text[:3000]
        except Exception as e:
            return f"Could not load page: {e}"
        finally:
            browser.close()


def find_prices(query: str) -> str:
    """
    Search Bing Shopping for a product and extract price information.
    Uses a headed browser with a real user agent to avoid bot detection.
    Returns a plain-text summary of what was found.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # visible window — avoids bot detection
            args=["--window-size=1,1", "--window-position=9999,9999"],  # tiny, off-screen
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            # Bing Shopping is less aggressive with bot detection than Google Shopping
            search_url = f"https://www.bing.com/shop?q={query.replace(' ', '+')}"
            page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)  # let dynamic content load

            results = []
            items = page.query_selector_all(".br-item")

            for item in items[:6]:
                title_el = item.query_selector(".br-primaryTextContainer")
                price_el = item.query_selector(".br-price")
                if title_el and price_el:
                    results.append(f"{title_el.inner_text().strip()} — {price_el.inner_text().strip()}")

            if not results:
                text = page.inner_text("body")
                return f"Here is what I found:\n{text[:2000]}"

            return "\n".join(results)
        except Exception as e:
            return f"Price search failed: {e}"
        finally:
            browser.close()
