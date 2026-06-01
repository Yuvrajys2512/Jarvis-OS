"""
Researcher — JARVIS's web-research specialist sub-agent.

It owns the visible Chrome window and the browser tools. Given a task in plain
language, it searches, opens pages, reads results — doing multi-step research when
needed — and returns a concise, factual synthesis for the orchestrator to speak.

The orchestrator reaches it through the `ask_researcher` tool (agents-as-tools).
The on_tool_start / on_tool_end hooks are threaded down from the orchestrator so the
browser tools still narrate and drive the HUD even though the *Researcher* (not
JARVIS itself) is the one calling them.
"""
from core.agent_base import Agent

RESEARCHER_PROMPT = """You are the Researcher, a specialist sub-agent of JARVIS.

You control a REAL, VISIBLE Chrome window the user is watching. Your job: take the
research task you are given and find the answer using your browser tools.

How you work:
- For a search, fact, or price lookup, call `search_google` (or `find_prices` for
  product prices). It opens Chrome, types the query into the search box on screen,
  presses search, and RETURNS the results text.
- If the snippet isn't enough, open a promising result with `get_page_text` and read
  it. Do this multi-step research until you actually have the answer.
- `search_google` opens the browser itself — never try to open Chrome first.

What you return:
- Reply with a concise, factual answer containing the REAL figures/details you found
  (e.g. the actual gold price), not a description of what you did.
- Write it as clean information for JARVIS to relay — not in first person, no persona.
- If you could not find the answer, say so plainly and briefly."""

# The browser tool schemas the Researcher exposes to the model (moved out of the
# orchestrator — these are now the Researcher's tools, not JARVIS's directly).
RESEARCHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Open the VISIBLE Chrome window, type the query into Google's search box letter-by-letter, press search, and return the results text. Use this for ANY web search or fact/price lookup. This opens the browser itself — do NOT open Chrome separately first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a specific URL in the visible Chrome window the user is watching.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to open"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_prices",
            "description": "Visibly search the web (in the on-screen Chrome window) for a product's price and return what was found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The product to search for"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_page_text",
            "description": "Open a URL in the visible Chrome window and return its on-screen text so you can read or summarise the page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to read"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_browser",
            "description": "Close the on-screen Chrome window.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _dispatch_research(name: str, args: dict, on_tool_start=None, on_tool_end=None) -> str:
    """Execute a Researcher tool. Accepts (and ignores) the hooks for a uniform
    dispatch signature — the Researcher doesn't nest further sub-agents."""
    if name == "search_google":
        from tools.browser import search_google
        return search_google(**args)
    elif name == "open_url":
        from tools.browser import open_url
        return open_url(**args)
    elif name == "find_prices":
        from tools.browser import find_prices
        return find_prices(**args)
    elif name == "get_page_text":
        from tools.browser import get_page_text
        return get_page_text(**args)
    elif name == "close_browser":
        from tools.browser import close_browser
        return close_browser()
    return f"Unknown research tool: {name}"


_researcher: Agent | None = None


def _get_researcher() -> Agent:
    global _researcher
    if _researcher is None:
        from core.agent import _get_client  # imported lazily to avoid an import cycle
        _researcher = Agent(
            name="researcher",
            system_prompt=RESEARCHER_PROMPT,
            tools=RESEARCHER_TOOLS,
            dispatch=_dispatch_research,
            client_getter=_get_client,
        )
    return _researcher


def ask_researcher(task: str, on_tool_start=None, on_tool_end=None) -> str:
    """Delegate a research task to the Researcher and return its findings.
    Hooks are threaded through so the browser tools still narrate + drive the HUD."""
    return _get_researcher().run(task, on_tool_start=on_tool_start, on_tool_end=on_tool_end)
