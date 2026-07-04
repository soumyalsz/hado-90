import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from runner.main import start_pipeline
from runner.logger import ws_logger

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"

app = FastAPI(title="Hado 90 v1.0.0 Web Endpoint Gateway")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the dashboard UI."""
    index_path = os.path.join("runner", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/run")
async def kick_off_pipeline():
    """Kicks off the audit pipeline in the background."""
    asyncio.create_task(start_pipeline())
    return {"status": "processing", "message": "Pipeline worker spawned successfully"}


@app.websocket("/ws/logs")
async def stream_logs(websocket: WebSocket):
    """Streams pipeline logs to the browser over WebSocket."""
    await websocket.accept()
    subscriber_queue = ws_logger.subscribe()
    try:
        while True:
            line = await subscriber_queue.get()
            await websocket.send_text(line)
            subscriber_queue.task_done()
    except WebSocketDisconnect:
        pass
    finally:
        ws_logger.unsubscribe(subscriber_queue)


if __name__ == "__main__":
    import uvicorn
    hot_reload = os.environ.get("RT_SANDBOX_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("runner.server:app", host="127.0.0.1", port=8000, reload=hot_reload)