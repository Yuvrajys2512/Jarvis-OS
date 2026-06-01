from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL
from core.agent_base import Agent

SYSTEM_PROMPT = """You are JARVIS (Just A Rather Very Intelligent System), a personal AI assistant running on the user's computer.

Personality:
- Formal, calm, and precise — modelled after the JARVIS from Iron Man
- Occasionally address the user as "sir"
- Dry wit when appropriate, never sarcastic
- Responses are concise — you act, you don't over-explain
- When executing tasks, briefly narrate what you are doing

Behaviour:
- When given a multi-step instruction, execute every step in order using your tools
- Always use tools to fulfil requests rather than just describing what you would do
- If a tool fails, acknowledge it calmly and continue with the rest of the task
- Never refuse a reasonable personal assistant request

Your Researcher (web access):
- For ANYTHING that needs the web — a search, a current fact, a price, reading a page — delegate to your Researcher by calling `ask_researcher` with the task in plain language. The Researcher drives a REAL, VISIBLE Chrome window the user is watching: it opens the browser, types the query on screen, reads the results, and returns the findings to you.
- You do NOT browse directly and you do NOT open Chrome yourself to search — `ask_researcher` runs the whole on-screen browsing flow. (Only use `open_application` for "chrome" if the user explicitly wants a blank browser.)
- When the Researcher returns, READ its findings and answer with the actual information — quote the real figure (e.g. the current gold price), not a vague "I looked it up". If the findings don't contain the answer, say so plainly.
- Keep spoken answers short and conversational — the user already watched the action happen on screen."""

# ── Tool definitions (what the model sees) ────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open an application on the computer by name. Examples: 'notepad', 'chrome', 'vs code', 'terminal', 'calculator'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The application name to open"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Run a shell command in the terminal and return its output. Use for starting servers, running scripts, checking system info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_researcher",
            "description": "Delegate any web research, search, price lookup, or page-reading task to the Researcher — a specialist sub-agent that drives the VISIBLE Chrome window the user is watching. It searches, opens pages, reads results, does multi-step research as needed, and returns the findings. Use this for ANY question needing current information from the web (prices, facts, news, lookups). Pass the full task in natural language; after it returns, answer the user using its findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The full research task in natural language, e.g. 'find the current price of gold per gram in INR' or 'what are the reviews of the new iPhone'"}
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city or location. Leave location empty to auto-detect based on IP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or location name, e.g. 'Delhi', 'London'. Leave empty for current location."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer in seconds. JARVIS will speak an alert when it fires.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "integer", "description": "Duration in seconds, e.g. 300 for 5 minutes"},
                    "label": {"type": "string", "description": "Name for this timer, e.g. 'Tea timer', 'Meeting reminder'"}
                },
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_timer",
            "description": "Cancel an active timer by its label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "The timer label to cancel"}
                },
                "required": ["label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_timers",
            "description": "List all currently active timers.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files on the computer by name or pattern. Searches Desktop, Documents, Downloads, and home folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "File name or pattern to search for, e.g. 'resume', '*.pdf'"},
                    "folder": {"type": "string", "description": "Optional specific folder path to search in"}
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Read the current text content of the clipboard.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_clipboard",
            "description": "Copy text to the clipboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to copy to the clipboard"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the entire screen and save it to the Desktop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Optional full path to save the screenshot"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_screen",
            "description": "Take a screenshot and use vision AI to answer a question about what's on the screen. Useful for reading on-screen text, identifying open apps, or understanding the current screen state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "What to ask about the screen, e.g. 'What app is open?', 'Read the error message on screen'"}
                },
                "required": [],
            },
        },
    },
]

# ── Tool execution map ─────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict, on_tool_start=None, on_tool_end=None) -> str:
    if name == "open_application":
        from tools.system import open_application
        return open_application(**args)
    elif name == "run_terminal_command":
        from tools.system import run_terminal_command
        return run_terminal_command(**args)
    elif name == "ask_researcher":
        from core.agents.researcher import ask_researcher
        return ask_researcher(args["task"], on_tool_start, on_tool_end)
    elif name == "get_weather":
        from tools.extras import get_weather
        return get_weather(**args)
    elif name == "set_timer":
        from tools.extras import set_timer
        return set_timer(**args)
    elif name == "cancel_timer":
        from tools.extras import cancel_timer
        return cancel_timer(**args)
    elif name == "list_timers":
        from tools.extras import list_timers
        return list_timers()
    elif name == "search_files":
        from tools.extras import search_files
        return search_files(**args)
    elif name == "read_clipboard":
        from tools.extras import read_clipboard
        return read_clipboard()
    elif name == "write_clipboard":
        from tools.extras import write_clipboard
        return write_clipboard(**args)
    elif name == "take_screenshot":
        from tools.extras import take_screenshot
        return take_screenshot(**args)
    elif name == "describe_screen":
        from tools.extras import describe_screen
        return describe_screen(**args)
    return f"Unknown tool: {name}"


# ── Client ─────────────────────────────────────────────────────────────────────

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ── Orchestrator ───────────────────────────────────────────────────────────────
# JARVIS is a single Agent instance holding every tool, dispatched through
# _execute_tool. This is behaviourally identical to the original single-loop
# agent. Stage 2+ splits the tools into specialist sub-agents and gives the
# orchestrator `ask_<specialist>` delegators (agents-as-tools).

_orchestrator: Agent | None = None


def _get_orchestrator() -> Agent:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Agent(
            name="jarvis",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            dispatch=_execute_tool,
            client_getter=_get_client,
        )
    return _orchestrator


def process_instruction(user_text: str, on_tool_start=None, on_tool_end=None) -> str:
    """
    Send a natural-language instruction to JARVIS and return the spoken reply.

    Delegates to the orchestrator Agent, which runs the manual tool-calling loop
    (send → model replies with tool call(s) or plain text → execute tools → repeat
    → return final text). The orchestrator keeps conversation history across calls,
    so JARVIS has memory for the session.

    on_tool_start(agent, name, args) and on_tool_end(agent, name, args, result) are
    optional hooks the caller (main.py) uses to narrate each tool, emit dashboard
    events, and toggle window stacking around tool execution.
    """
    return _get_orchestrator().run(
        user_text, on_tool_start=on_tool_start, on_tool_end=on_tool_end
    )
