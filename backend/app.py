import os
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import (
    init_db, get_user_by_username, create_user,
    get_all_projects, get_project, create_project, update_project, delete_project,
    get_project_subtasks, get_project_meeting_logs
)
from .services.meeting_room import meeting_hub
from .services.model_broker import model_broker
from .services.sandbox_runner import sandbox_manager
from .agents.manager_agent import manager_agent

app = FastAPI(title="Multi-Agent Collaborative System", version="1.0.0")

# Enable CORS for local cross-origin development if frontend is hosted separately
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database schema on startup
@app.on_event("startup")
def on_startup():
    init_db()

# --- Pydantic Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    name: Optional[str] = "Developer"

class CreateProjectRequest(BaseModel):
    title: str
    description: str
    goal: str
    storage_path: Optional[str] = None
    user_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class StartProjectRequest(BaseModel):
    provider: Optional[str] = "smart_simulation"
    custom_keys: Optional[Dict[str, str]] = None

class PostMessageRequest(BaseModel):
    sender: str
    role: Optional[str] = "Human Observer"
    content: str

class SaveFileRequest(BaseModel):
    filename: str
    content: str

class StartRunnerRequest(BaseModel):
    port: Optional[int] = None

class SettingsKeyRequest(BaseModel):
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    gemini: Optional[str] = None
    ollama_url: Optional[str] = None

# --- Auth Endpoints ---
@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "status": "success",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "created_at": user["created_at"]
        },
        "token": f"session_{user['id']}"
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = create_user(req.username, req.password, req.name or req.username)
    return {
        "status": "success",
        "user": user,
        "token": f"session_{user['id']}"
    }

# --- Projects Endpoints ---
@app.get("/api/projects")
def list_projects(user_id: Optional[str] = None):
    return {"projects": get_all_projects(user_id)}

@app.post("/api/projects")
def add_project(req: CreateProjectRequest):
    user_id = req.user_id or "admin-default"
    proj = create_project(
        title=req.title,
        description=req.description,
        goal=req.goal,
        user_id=user_id,
        storage_path=req.storage_path,
        config=req.config
    )
    return {"status": "success", "project": proj}

@app.get("/api/projects/{project_id}")
def get_project_details(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    subtasks = get_project_subtasks(project_id)
    logs = get_project_meeting_logs(project_id)
    room_state = meeting_hub.get_room_state(project_id)
    return {
        "project": proj,
        "subtasks": subtasks,
        "meeting_logs": logs,
        "room_state": room_state
    }

@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    success = delete_project(project_id)
    return {"status": "success", "deleted": success, "project_id": project_id}

@app.get("/api/projects/{project_id}/subtasks")
def list_subtasks(project_id: str):
    return {"subtasks": get_project_subtasks(project_id)}

# --- IDE Files & Editor Endpoints ---
@app.get("/api/projects/{project_id}/files")
def get_project_files(project_id: str):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    
    storage_path = proj.get("storage_path")
    if not storage_path or not os.path.exists(storage_path):
        return {"files": {}}

    files_dict = {}
    valid_exts = {".html", ".css", ".js", ".json", ".md", ".py", ".txt", ".sh", ".ts", ".jsx", ".tsx"}
    
    for root, _, files in os.walk(storage_path):
        for f in sorted(files):
            # Skip hidden mac metadata files
            if f.startswith(".") or f.startswith("._"):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts or not ext:
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, storage_path)
                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                    files_dict[rel_p] = {
                        "name": f,
                        "path": rel_p,
                        "extension": ext.lstrip("."),
                        "size": len(content),
                        "content": content
                    }
                except Exception:
                    pass

    return {
        "storage_path": storage_path,
        "files": files_dict
    }

@app.post("/api/projects/{project_id}/files/save")
def save_project_file(project_id: str, req: SaveFileRequest):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    
    storage_path = proj.get("storage_path")
    if not storage_path:
        raise HTTPException(status_code=400, detail="No storage path set for project")

    os.makedirs(storage_path, exist_ok=True)
    target_file = os.path.abspath(os.path.join(storage_path, req.filename))
    
    # Prevent directory traversal attacks
    if not target_file.startswith(os.path.abspath(storage_path)):
        raise HTTPException(status_code=400, detail="Invalid target file path")

    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(req.content)

    return {
        "status": "success",
        "filename": req.filename,
        "saved_path": target_file
    }

# --- Sandbox Runner on Port 8080 Endpoints ---
@app.post("/api/projects/{project_id}/runner/start")
def start_sandbox_runner(project_id: str, req: StartRunnerRequest):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    storage_path = proj.get("storage_path")
    if not storage_path:
        storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects", "app")
    
    try:
        os.makedirs(storage_path, exist_ok=True)
    except Exception:
        storage_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_projects", "app")
        os.makedirs(storage_path, exist_ok=True)

    result = sandbox_manager.start_project_server(project_id=project_id, target_directory=storage_path, port=req.port)
    return result

@app.post("/api/projects/{project_id}/runner/stop")
@app.post("/api/runner/force-stop")
def stop_sandbox_runner(project_id: Optional[str] = None):
    return sandbox_manager.stop_project_server()

@app.get("/api/projects/{project_id}/runner/status")
@app.get("/api/runner/status")
def get_sandbox_runner_status(project_id: Optional[str] = None):
    return sandbox_manager.get_status()

# --- Meeting Room Endpoints ---
@app.get("/api/projects/{project_id}/meeting/logs")
def get_meeting_logs(project_id: str):
    return {"logs": get_project_meeting_logs(project_id)}

@app.get("/api/projects/{project_id}/meeting/state")
def get_meeting_state(project_id: str):
    return {"state": meeting_hub.get_room_state(project_id)}

@app.post("/api/projects/{project_id}/meeting/message")
async def post_human_message(
    project_id: str,
    req: PostMessageRequest,
    background_tasks: BackgroundTasks
):
    log = await meeting_hub.post_message(
        project_id=project_id,
        sender=req.sender,
        role=req.role or "Human Observer",
        content=req.content,
        message_type="human_input"
    )
    
    # Manager agent actively reviews human input and participates
    background_tasks.add_task(
        manager_agent.handle_human_message,
        project_id,
        req.sender,
        req.content
    )
    
    return {"status": "success", "message": log}

# --- Real-Time Server-Sent Events (SSE) Stream ---
@app.get("/api/projects/{project_id}/meeting/stream")
async def stream_meeting_events(project_id: str):
    queue = meeting_hub.subscribe(project_id)

    async def event_generator():
        try:
            # First send initial ping and current state
            initial_state = meeting_hub.get_room_state(project_id)
            yield f"data: {json.dumps({'type': 'init', 'room_state': initial_state})}\n\n"

            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            meeting_hub.unsubscribe(project_id, queue)
        except Exception:
            meeting_hub.unsubscribe(project_id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Start Multi-Agent Orchestration ---
@app.post("/api/projects/{project_id}/start")
async def start_orchestration(
    project_id: str,
    req: StartProjectRequest,
    background_tasks: BackgroundTasks
):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Run orchestration in background
    background_tasks.add_task(
        manager_agent.run_project_orchestration,
        project_id=project_id,
        provider=req.provider or "smart_simulation",
        custom_keys=req.custom_keys
    )

    return {
        "status": "orchestration_started",
        "project_id": project_id,
        "provider": req.provider
    }

# --- Live App Preview Endpoint ---
@app.get("/apps/{project_id}")
@app.get("/apps/{project_id}/")
@app.get("/apps/{project_id}/{file_path:path}")
def serve_generated_app(project_id: str, file_path: str = "index.html"):
    proj = get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    
    storage_path = proj.get("storage_path")
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="App files have not been generated yet.")

    clean_file = file_path.strip("/") if file_path and file_path.strip("/") else "index.html"
    target_file = os.path.join(storage_path, clean_file)
    
    if not os.path.exists(target_file):
        # Fallback to index.html if exists
        target_file = os.path.join(storage_path, "index.html")
        if not os.path.exists(target_file):
            raise HTTPException(status_code=404, detail="Requested file not found in generated project.")

    # Determine media type for html
    media_type = "text/html" if target_file.endswith(".html") else None
    return FileResponse(target_file, media_type=media_type)

# --- Settings & Keys Endpoints ---
@app.post("/api/settings/keys")
def update_api_keys(req: SettingsKeyRequest):
    keys_dict = {}
    if req.openai is not None: keys_dict["openai"] = req.openai
    if req.anthropic is not None: keys_dict["anthropic"] = req.anthropic
    if req.gemini is not None: keys_dict["gemini"] = req.gemini
    if req.ollama_url is not None: keys_dict["ollama_url"] = req.ollama_url
    model_broker.update_keys(keys_dict)
    return {"status": "keys_updated"}

@app.get("/api/settings/status")
def get_model_status():
    return {
        "openai_configured": bool(model_broker.openai_key),
        "anthropic_configured": bool(model_broker.anthropic_key),
        "gemini_configured": bool(model_broker.gemini_key),
        "ollama_url": model_broker.ollama_url,
        "smart_simulation_available": True
    }

# --- Mount Static Frontend ---
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
