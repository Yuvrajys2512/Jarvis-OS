"""
Agent — the reusable tool-calling brain behind JARVIS.

A single Agent owns one system prompt, one set of tools, one dispatch function,
and its own conversation history. `run()` is the manual tool-calling loop that
used to live inline in core/agent.process_instruction():

    send messages → model replies with tool call(s) or plain text
      → if tool calls: execute each via dispatch, append results, repeat
      → if plain text: that's the final answer

This is deliberately framework-free. The multi-agent design (Stage 2+) is just
more Agent instances: a specialist is an Agent with a narrower prompt + tool set,
and the orchestrator calls it through an `ask_<specialist>` dispatch entry — i.e.
agents-as-tools, all built on this one class.
"""
import json
from typing import Callable, Optional

from config.settings import GROQ_MODEL

# Hook signatures (used by main.py to narrate + drive the HUD around each tool):
#   on_tool_start(agent_name, tool_name, args)
#   on_tool_end(agent_name, tool_name, args, result)
OnToolStart = Callable[[str, str, dict], None]
OnToolEnd = Callable[[str, str, dict, str], None]


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list,
        dispatch: Callable[[str, dict], str],
        model: str = GROQ_MODEL,
        client_getter: Optional[Callable] = None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools                  # tool JSON schemas the model sees
        self.dispatch = dispatch            # (tool_name, args) -> result string
        self.model = model
        self._client_getter = client_getter
        self._client = None
        self.history: list = []             # session memory, preserved across run() calls

    @property
    def client(self):
        if self._client is None:
            if self._client_getter is None:
                raise RuntimeError(f"Agent {self.name!r} has no client_getter")
            self._client = self._client_getter()
        return self._client

    def run(
        self,
        user_text: str,
        on_tool_start: Optional[OnToolStart] = None,
        on_tool_end: Optional[OnToolEnd] = None,
    ) -> str:
        """Run the tool-calling loop to completion and return the final text reply."""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_text})

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )

            message = response.choices[0].message
            messages.append(message)

            if not message.tool_calls:
                # No tool calls — this is the final response.
                final_text = message.content or ""
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": final_text})
                # Keep the last 40 messages (~20 turns) to prevent hitting context limits.
                if len(self.history) > 40:
                    self.history = self.history[-40:]
                return final_text

            # Execute each tool call and feed results back into the loop.
            for tc in message.tool_calls:
                args = json.loads(tc.function.arguments)
                name = tc.function.name

                if on_tool_start:
                    on_tool_start(self.name, name, args)

                print(f"  [{self.name}:tool] {name}({args})")
                try:
                    # Pass the hooks into dispatch so a delegating tool (e.g.
                    # ask_researcher) can thread them into its sub-agent's run(),
                    # keeping narration + HUD events alive one level down.
                    result = self.dispatch(name, args, on_tool_start, on_tool_end)
                except Exception as e:
                    result = f"Tool error: {e}"
                print(f"  [{self.name}:result] {str(result)[:120]}")

                if on_tool_end:
                    on_tool_end(self.name, name, args, result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
