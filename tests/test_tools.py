"""
Phase 5 verify — test each system tool directly (no voice needed).
Run and watch what happens on your desktop.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.system import open_application, run_terminal_command, open_recent_vs_code_project, get_recent_vs_code_project

print("=== System Tools Test ===\n")

# Test 1: run a terminal command
print("Test 1: run_terminal_command('echo Hello from JARVIS')")
output = run_terminal_command("echo Hello from JARVIS")
print(f"  Output: {output}\n")

# Test 2: run a useful command
print("Test 2: run_terminal_command('dir /b C:\\\\Users\\\\Public')")
output = run_terminal_command("dir /b C:\\Users\\Public")
print(f"  Output: {output}\n")

# Test 3: open Notepad
print("Test 3: open_application('notepad') — Notepad should open on your desktop")
result = open_application("notepad")
print(f"  Result: {result}\n")

# Test 4: find recent VS Code project
print("Test 4: get_recent_vs_code_project()")
project = get_recent_vs_code_project()
print(f"  Most recent project: {project if project else '(none found)'}\n")

print("All tool tests complete.")
