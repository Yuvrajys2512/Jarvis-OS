import re
import subprocess
import time
import random
import pyautogui
from playwright.sync_api import sync_playwright, Page


# ── Window tile system ────────────────────────────────────────────────────────
# JARVIS lives in the RIGHT 38% of the screen.
# Every Chrome window we open goes into the LEFT 62%, tiled so nothing overlaps.

_chrome_count = 0   # how many windows we've opened this session

JARVIS_FRACTION = 0.38   # reserve this fraction on the right for the dashboard

# Win32 Add-Type block (defined once; wrapped in try/catch so re-runs don't error)
_PS_ADDTYPE = r'''
try {
  Add-Type -TypeDefinition @"
  using System;
  using System.Runtime.InteropServices;
  public class JWin32 {
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr z, int x, int y, int cx, int cy, uint f);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int n);
  }
"@
} catch {}
'''


def _avail():
    """Available screen area to the left of the JARVIS panel."""
    sw, sh = pyautogui.size()
    return int(sw * (1 - JARVIS_FRACTION)), sh - 52   # subtract taskbar


def _slots(n: int):
    """Return list of (x, y, w, h) for n non-overlapping tiles."""
    aw, ah = _avail()
    if n == 1: return [(0, 0, aw, ah)]
    if n == 2: return [(0, 0, aw, ah // 2), (0, ah // 2, aw, ah // 2)]
    if n == 3: return [(0, 0, aw // 2, ah), (aw // 2, 0, aw // 2, ah // 2), (aw // 2, ah // 2, aw // 2, ah // 2)]
    # 4 or more → 2×2 grid, extras stacked in thirds
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    cw, ch = aw // cols, ah // rows
    return [(( i % cols) * cw, (i // cols) * ch, cw, ch) for i in range(n)]


def _arrange():
    """Reposition every Chrome window (excluding JARVIS) into its tile slot."""
    tiles = _slots(_chrome_count)
    if not tiles:
        return

    # Build PowerShell position array
    pos_lines = '\n'.join(
        f'  @{{x={x};y={y};w={w};h={h}}}'
        for x, y, w, h in tiles
    )

    ps = f'''
{_PS_ADDTYPE}
$wins = Get-Process -Name chrome -ErrorAction SilentlyContinue |
        Where-Object {{ [int64]$_.MainWindowHandle -ne 0 -and
                       $_.MainWindowTitle -notmatch "JARVIS|localhost|7777" }} |
        Sort-Object StartTime
$slots = @(
{pos_lines}
)
for ($i = 0; $i -lt [Math]::Min($wins.Count, $slots.Count); $i++) {{
  $h = $wins[$i].MainWindowHandle
  [JWin32]::ShowWindow($h, 9)
  [JWin32]::SetWindowPos($h, [IntPtr]::Zero,
    $slots[$i].x, $slots[$i].y, $slots[$i].w, $slots[$i].h, 0x0054)
}}
'''
    subprocess.run(['powershell', '-Command', ps], capture_output=True, timeout=10)


def reset_layout():
    """Call when JARVIS goes idle to reset the tile counter."""
    global _chrome_count
    _chrome_count = 0


def _open_chrome_window():
    """Open a new Chrome window, increment counter, rearrange all tiles."""
    global _chrome_count
    _chrome_count += 1
    subprocess.Popen('start chrome --new-window', shell=True)
    time.sleep(2.2)     # Chrome loads
    _arrange()          # snap all windows into their slots
    time.sleep(0.4)


def _focus_slot_and_type(query: str):
    """Click into our tile's address bar and type the query theatrically."""
    tiles = _slots(_chrome_count)
    if not tiles:
        return
    x, y, w, h = tiles[-1]   # our tile is always the last one

    # Click the address bar area of our tile
    pyautogui.click(x + w // 2, y + 45)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.35)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)

    # Type word by word, letter by letter
    for i, word in enumerate(query.strip().split()):
        pyautogui.write(word, interval=0.07)
        if i < len(query.strip().split()) - 1:
            pyautogui.press('space')
            time.sleep(0.16)

    time.sleep(0.45)
    pyautogui.press('enter')


# ── Public tools ──────────────────────────────────────────────────────────────

def open_url(url: str) -> str:
    """Open a URL in a tiled Chrome window that doesn't overlap JARVIS."""
    _open_chrome_window()
    _focus_slot_and_type(url)
    return f"Opened {url}."


def search_google(query: str) -> str:
    """
    Open a new tiled Chrome window, wait for it to load, then type the search
    query letter-by-letter into the address bar and press Enter.
    All existing Chrome windows rearrange so nothing overlaps JARVIS.
    """
    _open_chrome_window()
    _focus_slot_and_type(query)
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
