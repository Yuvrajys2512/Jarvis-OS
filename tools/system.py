import subprocess
import os
import json
from pathlib import Path

# Maps friendly names → what to actually launch on Windows
APP_ALIASES = {
    "notepad": "notepad.exe",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "calculator": "calc.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "cmd": "cmd.exe",
    "spotify": "spotify",
    "discord": "discord",
}


def open_application(name: str) -> str:
    """
    Open an application by friendly name.
    Returns a status string describing what happened.
    """
    key = name.lower().strip()
    command = APP_ALIASES.get(key, key)  # fall back to the name itself if not in aliases

    try:
        subprocess.Popen(command, shell=True)
        return f"Opened {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"


def run_terminal_command(command: str) -> str:
    """
    Run a shell command and return its output as a string.
    Captures both stdout and stderr.
    Times out after 30 seconds to prevent hanging.
    """
    # Safety check — block destructive commands
    blocked = ["rm -rf", "format", "del /f", "rd /s", "shutdown", "rmdir /s"]
    if any(b in command.lower() for b in blocked):
        return "Blocked: that command is potentially destructive. Please run it manually."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "(command ran with no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


def get_recent_vs_code_project() -> str:
    """
    Read VS Code's recently opened files list and return the most recent project path.
    VS Code stores this in a JSON file in AppData.
    """
    storage_path = Path(os.environ["APPDATA"]) / "Code" / "User" / "globalStorage" / "storage.json"

    if not storage_path.exists():
        return ""

    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("openedPathsList", {}).get("workspaces3", [])

        for entry in entries:
            uri = entry if isinstance(entry, str) else entry.get("folderUri", "")
            if uri.startswith("file:///"):
                path = uri.replace("file:///", "").replace("/", "\\")
                if os.path.isdir(path):
                    return path

        return ""
    except Exception:
        return ""


def open_recent_vs_code_project() -> str:
    """Open the most recently used VS Code project folder."""
    project_path = get_recent_vs_code_project()
    if not project_path:
        return "Could not find a recent VS Code project."
    result = subprocess.Popen(f'code "{project_path}"', shell=True)
    return f"Opened VS Code project: {project_path}"
