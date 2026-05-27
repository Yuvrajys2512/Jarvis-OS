"""
Phase 6 verify — browser automation tests.
Expected:
  - Test 1: your default browser opens Google
  - Test 2: headless browser fetches Wikipedia text
  - Test 3: Google Shopping prices extracted
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.browser import search_google, get_page_text, find_prices

print("=== Browser Tools Test ===\n")

print("Test 1: search_google('Python programming') — browser should open")
result = search_google("Python programming")
print(f"  Result: {result}\n")

print("Test 2: get_page_text (headless, fetching Wikipedia)...")
text = get_page_text("https://en.wikipedia.org/wiki/Iron_Man")
print(f"  First 200 chars: {text[:200]}\n")

print("Test 3: find_prices('mechanical keyboard')...")
prices = find_prices("mechanical keyboard")
print(f"  Prices found:\n{prices}\n")

print("All browser tests complete.")
