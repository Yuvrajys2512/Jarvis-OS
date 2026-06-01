import re
import time
import atexit
import subprocess
from pathlib import Path

import pyautogui
from playwright.sync_api import sync_playwright


# ══════════════════════════════════════════════════════════════════════════════
#  VISIBLE BROWSER ENGINE  (dedicated JARVIS Chrome profile)
# ══════════════════════════════════════════════════════════════════════════════
# JARVIS drives ONE real, visible Chrome window using its own profile directory.
# Sign in to Google once in that window and it's remembered forever — the profile
# picker / "choose an account" screen never appears again, because a persistent
# context always uses exactly this one profile.
#
# Everything happens on screen, in the foreground: the window opens, the query is
# typed into the real search box letter-by-letter, search is pressed, and the
# results are read back out of the same window the user is watching.

_PROFILE_DIR = Path.home() / ".jarvis" / "chrome-profile"

_pw = None     # Playwright instance (started once, on the pipeline thread)
_ctx = None    # persistent BrowserContext
_page = None   # the visible page we drive

# How fast JARVIS "types". Lower = faster. ~85ms/char looks deliberate and human.
TYPE_DELAY_MS = 85


def _launch() -> None:
    """Start Playwright (once) and open the visible Chrome window with our profile."""
    global _pw, _ctx, _page
    if _pw is None:
        _pw = sync_playwright().start()
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    launch_kwargs = dict(
        user_data_dir=str(_PROFILE_DIR),
        headless=False,
        no_viewport=True,                 # let the page fill the real window
        # Strip the automation tells that make Google show "unusual traffic":
        ignore_default_args=["--enable-automation"],
        args=[
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--disable-features=Translate",
            "--disable-blink-features=AutomationControlled",  # hide navigator.webdriver
        ],
    )
    try:
        # Use the user's real Google Chrome for the most authentic look.
        _ctx = _pw.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
    except Exception:
        # Fall back to Playwright's bundled Chromium if real Chrome can't be driven.
        _ctx = _pw.chromium.launch_persistent_context(**launch_kwargs)

    _page = _ctx.pages[0] if _ctx.pages else _ctx.new_page()
    _page.set_default_timeout(20000)


def _reset() -> None:
    """Tear down the context/page (e.g. after the user closed the window)."""
    global _ctx, _page
    try:
        if _ctx is not None:
            _ctx.close()
    except Exception:
        pass
    _ctx = None
    _page = None


def _get_page():
    """Return the live visible page, (re)launching Chrome if it was closed."""
    global _page
    try:
        if _page is not None and not _page.is_closed():
            return _page
    except Exception:
        pass
    _reset()
    _launch()
    return _page


def _shutdown_browser() -> None:
    """Close the browser and stop Playwright when JARVIS exits."""
    global _pw
    _reset()
    try:
        if _pw is not None:
            _pw.stop()
    except Exception:
        pass
    _pw = None


atexit.register(_shutdown_browser)


# ── Step emitter ────────────────────────────────────────────────────────────────

def _emit_step(text: str) -> None:
    """Push a sub-step label to the dashboard HUD. Silently no-ops if server isn't running."""
    try:
        import server
        server.emit("substep", text=text)
    except Exception:
        pass


# ── On-screen helpers ───────────────────────────────────────────────────────────

# Google's cookie/consent wall (varies by region) blocks the search box until
# dismissed. These cover the common variants.
_CONSENT_SELECTORS = [
    "#L2AGLb",                          # Google "Accept all" button id
    "button:has-text('Accept all')",
    "button:has-text('I agree')",
    "button:has-text('Accept the use')",
    "button:has-text('Reject all')",
]


def _dismiss_google_consent(page) -> None:
    """If Google shows its consent wall, click through it so search can proceed."""
    for sel in _CONSENT_SELECTORS:
        try:
            page.locator(sel).first.click(timeout=1000)
            page.wait_for_timeout(400)
            return
        except Exception:
            continue


def _type_theatrically(locator, text: str, delay: int = TYPE_DELAY_MS) -> None:
    """Type text one character at a time so the user can watch it appear."""
    try:
        locator.press_sequentially(text, delay=delay)
    except Exception:
        locator.type(text, delay=delay)  # older Playwright fallback


def _read_results(page) -> str:
    """Pull the visible answer/results text out of a Google results page."""
    for sel in ("#search", "#rso", "#center_col", "body"):
        try:
            txt = page.locator(sel).first.inner_text(timeout=3000)
            txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
            if txt:
                return txt[:2500]
        except Exception:
            continue
    return ""


def _normalise_url(url: str) -> str:
    return url if re.match(r"^https?://", url) else "https://" + url


def _visible_search(query: str) -> str:
    """
    The core 'magic' flow, all on screen:
      open/raise Chrome → go to Google → type the query letter-by-letter →
      press Enter → wait for results → read them back.
    Returns the results text so JARVIS can answer with the actual numbers.
    Each stage emits a sub-step event so the HUD label updates in real time.
    """
    _emit_step("OPENING CHROME")
    page = _get_page()
    page.bring_to_front()

    _emit_step("NAVIGATING  ›  GOOGLE")
    page.goto("https://www.google.com/", wait_until="domcontentloaded")
    _dismiss_google_consent(page)

    box = page.locator("textarea[name='q'], input[name='q']").first
    box.click()
    time.sleep(0.3)

    short_q = query if len(query) <= 38 else query[:35] + "..."
    _emit_step(f"TYPING  ›  {short_q}")
    _type_theatrically(box, query)
    time.sleep(0.45)

    _emit_step("SEARCHING...")
    box.press("Enter")

    try:
        page.wait_for_selector("#search, #rso, #center_col", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(1200)

    _emit_step("READING RESULTS")
    results = _read_results(page)
    if not results:
        return f"Searched Google for '{query}', but the results didn't come back cleanly."
    return f"Search results for '{query}':\n{results}"


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC TOOLS  (called by the agent)
# ══════════════════════════════════════════════════════════════════════════════

def search_google(query: str) -> str:
    """
    Open the visible Chrome window, type the query into Google's search box
    letter-by-letter, press search, and return the results text.
    """
    return _visible_search(query)


def find_prices(query: str) -> str:
    """
    Visibly search the web for a product's price and return what was found.
    Same on-screen flow as search_google, focused on price.
    """
    q = query if "price" in query.lower() else f"{query} price"
    return _visible_search(q)


def open_url(url: str) -> str:
    """Open a specific URL in the visible Chrome window the user is watching."""
    url = _normalise_url(url)
    short = url.replace("https://", "").replace("http://", "")[:40]
    _emit_step(f"OPENING  ›  {short}")
    page = _get_page()
    page.bring_to_front()
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(600)
        title = (page.title() or "").strip()
        _emit_step(f"LOADED  ›  {title[:40]}" if title else "LOADED")
        return f'Opened {url}' + (f' — "{title}".' if title else ".")
    except Exception as e:
        return f"Could not open {url}: {e}"


def get_page_text(url: str) -> str:
    """
    Open a URL in the visible Chrome window and return its visible text
    (first 3000 chars) so JARVIS can read/summarise the page.
    """
    url = _normalise_url(url)
    short = url.replace("https://", "").replace("http://", "")[:40]
    _emit_step(f"READING PAGE  ›  {short}")
    page = _get_page()
    page.bring_to_front()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(800)
        _emit_step("EXTRACTING TEXT")
        text = page.locator("body").inner_text()
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text[:3000]
    except Exception as e:
        return f"Could not load page: {e}"


def close_browser() -> str:
    """Close the JARVIS Chrome window."""
    _emit_step("CLOSING BROWSER")
    _reset()
    return "Closed the browser."


# ══════════════════════════════════════════════════════════════════════════════
#  LEGACY WINDOW-TILE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
# Only used by the standalone showcase in demo.py. The live assistant no longer
# tiles windows — apps simply open in the foreground over the JARVIS backdrop.

_chrome_count = 0
JARVIS_FRACTION = 0.38   # demo.py reads this to size its left-area rectangles

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
    sw, sh = pyautogui.size()
    return int(sw * (1 - JARVIS_FRACTION)), sh - 52


def _slots(n: int):
    aw, ah = _avail()
    if n == 1: return [(0, 0, aw, ah)]
    if n == 2: return [(0, 0, aw, ah // 2), (0, ah // 2, aw, ah // 2)]
    if n == 3: return [(0, 0, aw // 2, ah), (aw // 2, 0, aw // 2, ah // 2), (aw // 2, ah // 2, aw // 2, ah // 2)]
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    cw, ch = aw // cols, ah // rows
    return [((i % cols) * cw, (i // cols) * ch, cw, ch) for i in range(n)]


def _arrange():
    tiles = _slots(_chrome_count)
    if not tiles:
        return
    pos_lines = '\n'.join(f'  @{{x={x};y={y};w={w};h={h}}}' for x, y, w, h in tiles)
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
    global _chrome_count
    _chrome_count = 0


def _open_chrome_window():
    global _chrome_count
    _chrome_count += 1
    subprocess.Popen('start chrome --new-window', shell=True)
    time.sleep(2.2)
    _arrange()
    time.sleep(0.4)


def _focus_slot_and_type(query: str):
    tiles = _slots(_chrome_count)
    if not tiles:
        return
    x, y, w, h = tiles[-1]
    pyautogui.click(x + w // 2, y + 45)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.35)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.1)
    words = query.strip().split()
    for i, word in enumerate(words):
        pyautogui.write(word, interval=0.07)
        if i < len(words) - 1:
            pyautogui.press('space')
            time.sleep(0.16)
    time.sleep(0.45)
    pyautogui.press('enter')
