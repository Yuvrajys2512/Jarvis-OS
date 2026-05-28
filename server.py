"""
JARVIS Dashboard Server
Runs a local FastAPI + WebSocket server so the browser dashboard
receives real-time events from the JARVIS pipeline.
"""
import asyncio
import threading
import webbrowser
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

_clients: list[WebSocket] = []
_loop: asyncio.AbstractEventLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _loop
    _loop = asyncio.get_running_loop()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def dashboard():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    _clients.append(ws)
    try:
        while True:
            # Keep connection alive with a heartbeat every 20s
            await asyncio.sleep(20)
            await ws.send_json({"type": "ping"})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        if ws in _clients:
            _clients.remove(ws)


async def _broadcast(event: dict):
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _clients:
            _clients.remove(ws)


def emit(event_type: str, **kwargs) -> None:
    """
    Call this from anywhere in the JARVIS pipeline to push a real-time
    event to the dashboard. Thread-safe — works from the main thread.
    """
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(
            _broadcast({"type": event_type, **kwargs}),
            _loop,
        )


def _run_server() -> None:
    config = uvicorn.Config(app, host="127.0.0.1", port=7777, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def launch() -> None:
    """Start the server in a background daemon thread and open the dashboard."""
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    # Give uvicorn a moment to bind the port before opening the browser
    import time
    time.sleep(1.5)
    webbrowser.open("http://localhost:7777")
