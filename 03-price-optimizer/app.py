from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from price_optimizer.workflow import run_agentic_workflow

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Agentic Price Optimizer")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


class AnalyzeRequest(BaseModel):
    query: str
    image_url: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> StreamingResponse:
    def event_stream():
        event_queue: "queue.Queue[dict | None]" = queue.Queue()

        def emit(event_type: str, data: dict) -> None:
            event_queue.put({"type": event_type, "data": data})

        def worker() -> None:
            try:
                run_agentic_workflow(
                    query=payload.query,
                    image_url=payload.image_url,
                    emit=emit,
                )
            except Exception as exc:
                emit("error", {"message": str(exc)})
            finally:
                event_queue.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event = event_queue.get()
            if event is None:
                break
            yield json.dumps(event) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
