from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Live Weather Radar App with 7-day forecast and temperature toggle API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health():
    return {"status": "healthy", "service": "Live Weather Radar App with 7-day forecast and temperature toggle"}

@app.get("/api/data")
def get_data():
    return {"service": "Live Weather Radar App with 7-day forecast and temperature toggle", "status": "active"}

static_dir = os.path.dirname(__file__)
if os.path.exists(os.path.join(static_dir, "index.html")):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)