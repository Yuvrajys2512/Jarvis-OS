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
