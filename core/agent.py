import json
from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL

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
- Never refuse a reasonable personal assistant request"""

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
            "name": "search_google",
            "description": "Open Google in the browser and search for a query.",
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
            "description": "Open a specific URL in the browser.",
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
            "description": "Search online for the price of a product. Returns a list of products with prices.",
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
            "description": "Fetch and read the visible text content of a webpage.",
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

def _execute_tool(name: str, args: dict) -> str:
    if name == "open_application":
        from tools.system import open_application
        return open_application(**args)
    elif name == "run_terminal_command":
        from tools.system import run_terminal_command
        return run_terminal_command(**args)
    elif name == "search_google":
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


# ── Agent setup ────────────────────────────────────────────────────────────────

_client: Groq | None = None
_conversation: list = []


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def process_instruction(user_text: str) -> str:
    """
    Send a natural language instruction to Llama 3.3 on Groq.
    Runs the tool-calling loop manually:
      1. Send messages → model replies with tool call(s) or plain text
      2. If tool calls: execute each, append results, repeat
      3. If plain text: return it
    Conversation history is preserved across calls so JARVIS has memory.
    """
    client = _get_client()

    # Build message history — system prompt + full conversation + new user message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_conversation)
    messages.append({"role": "user", "content": user_text})

    while True:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            # No tool calls — we have the final response
            final_text = message.content or ""
            # Save this exchange to conversation history
            _conversation.append({"role": "user", "content": user_text})
            _conversation.append({"role": "assistant", "content": final_text})
            return final_text

        # Execute each tool call and collect results
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  [tool] {tc.function.name}({args})")
            try:
                result = _execute_tool(tc.function.name, args)
            except Exception as e:
                result = f"Tool error: {e}"
            print(f"  [result] {str(result)[:120]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })
