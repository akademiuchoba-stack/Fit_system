from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/api/status")
async def get_status():
    return {"status": "online", "message": "Система Идеальный Припуск готова к работе!"}

app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))
.