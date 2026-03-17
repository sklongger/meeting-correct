from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import asyncio
import json
import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    _main_loop = asyncio.get_event_loop()

    def run_watchdog():
        event_handler = FileChangeHandler()
        observer = PollingObserver()
        observer.schedule(event_handler, ".", recursive=False)
        observer.start()
        observer.join()

    thread = threading.Thread(target=run_watchdog, daemon=True)
    thread.start()

    yield


app = FastAPI(lifespan=lifespan)

RESULTS_JSON = "fact_check_results.json"
TRANSCRIPT_FILE = "transcript.txt"
websocket_clients = []
_main_loop = None


class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if (
            event.src_path.endswith(RESULTS_JSON)
            or event.src_path.endswith("./" + RESULTS_JSON)
            or event.src_path.endswith(TRANSCRIPT_FILE)
            or event.src_path.endswith("./" + TRANSCRIPT_FILE)
        ):
            if _main_loop and _main_loop.is_running():
                asyncio.run_coroutine_threadsafe(push_to_clients(), _main_loop)


def read_results():
    results = []
    transcript = ""

    try:
        if os.path.exists(RESULTS_JSON):
            with open(RESULTS_JSON, "r", encoding="utf-8") as f:
                results = json.load(f)
    except:
        pass

    try:
        if os.path.exists(TRANSCRIPT_FILE):
            with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
                transcript = f.read()
    except:
        pass

    return results, transcript


async def push_to_clients():
    results, transcript = read_results()
    data = {"results": results, "transcript": transcript}

    for client in list(websocket_clients):
        try:
            await client.send_json(data)
        except:
            if client in websocket_clients:
                websocket_clients.remove(client)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)

    results, transcript = read_results()
    if results or transcript:
        await websocket.send_json({"results": results, "transcript": transcript})

    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


@app.get("/")
async def get_html():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


def run_server():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")


if __name__ == "__main__":
    run_server()
