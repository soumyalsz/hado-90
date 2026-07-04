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

app = FastAPI(title="RT-SANDBOX Web Endpoint Gateway")

# Ensure your report workspace paths exist cleanly on disk layout
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

@app.get("/", response_class=HTMLResponse)
async def read_dashboard_root():
    """Serves the main application control dashboard interface."""
    index_path = os.path.join("runner", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/run")
async def trigger_sandbox_pipeline():
    """Spawns the test orchestrator sequence as a decoupled background loop task."""
    # Execute loop concurrently inside active asyncio worker context
    asyncio.create_task(start_pipeline())
    return {"status": "processing", "message": "Pipeline worker spawned successfully"}

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    """Binds live browser sessions directly into your pipeline execution queue logs."""
    await websocket.accept()
    log_queue = ws_logger.register_client()
    try:
        while True:
            # Non-blocking pull from your custom global async logger queue
            log_message = await log_queue.get()
            await websocket.send_text(log_message)
            log_queue.task_done()
    except WebSocketDisconnect:
        pass
    finally:
        ws_logger.unregister_client(log_queue)

if __name__ == "__main__":
    import uvicorn
    reload_enabled = os.environ.get("RT_SANDBOX_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("runner.server:app", host="127.0.0.1", port=8000, reload=reload_enabled)