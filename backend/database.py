import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage.db")

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        storage_path TEXT,
        user_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'created',
        goal TEXT,
        config TEXT,
        deliverable TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
    # Gracefully ensure storage_path column exists in existing DB
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN storage_path TEXT")
    except Exception:
        pass
    
    # Subtasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subtasks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        worker_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        assigned_to TEXT,
        dependencies TEXT,
        output TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    """)
    
    # Meeting Room Messages / Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meeting_logs (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        role TEXT NOT NULL,
        message_type TEXT NOT NULL DEFAULT 'chat',
        content TEXT NOT NULL,
        metadata TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    """)
    
    # Default demo user
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, username, password, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "admin", "admin123", "Lead Architect", datetime.utcnow().isoformat())
        )
    
    # Preload sample project if empty
    cursor.execute("SELECT COUNT(*) as count FROM projects")
    count = cursor.fetchone()["count"]
    if count == 0:
        demo_user_id = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
        sample_id = str(uuid.uuid4())
        sample_time = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO projects (id, title, description, user_id, status, goal, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample_id,
                "Smart Task Manager & Kanban Microservice",
                "Full-stack collaborative task board with real-time sync, category filtering, and persistence.",
                demo_user_id,
                "ready",
                "Build a full-stack modern task management microservice with REST API, responsive UI, categories, and test suite.",
                json.dumps({"model": "smart_simulation", "parallel_workers": 4}),
                sample_time,
                sample_time
            )
        )
        
    conn.commit()
    conn.close()

# User Helpers
def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username: str, password: str, name: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO users (id, username, password, name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, password, name, now)
    )
    conn.commit()
    conn.close()
    return {"id": user_id, "username": username, "name": name, "created_at": now}

# Project Helpers
def get_all_projects(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("config"):
            try: d["config"] = json.loads(d["config"])
            except: pass
        if d.get("deliverable"):
            try: d["deliverable"] = json.loads(d["deliverable"])
            except: pass
        result.append(d)
    return result

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get("config"):
        try: d["config"] = json.loads(d["config"])
        except: pass
    if d.get("deliverable"):
        try: d["deliverable"] = json.loads(d["deliverable"])
        except: pass
    return d

def sanitize_storage_path(storage_path: Optional[str], title: str, add_timestamp: bool = False) -> str:
    import re
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title.lower().strip()).strip("_") or "project"
    ts_suffix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if not storage_path or not storage_path.strip():
        folder_name = f"{safe_title}_{ts_suffix}" if add_timestamp else safe_title
        return os.path.join(workspace_root, "generated_projects", folder_name)
    
    raw = storage_path.strip()
    
    # If user pasted a terminal prompt
    match = re.search(r"[\s:@~]([a-zA-Z0-9_\-\.\/]+)\s*[%$#]\s*$", raw)
    if match:
        raw = match.group(1).strip()
    elif raw.endswith("%") or raw.endswith("$") or raw.endswith("#"):
        tokens = raw.rstrip("%$# ").split()
        if tokens:
            raw = tokens[-1]

    # Expand user ~
    expanded = os.path.expanduser(raw)
    
    # Auto-resolve mac user home directory discrepancies
    if expanded.startswith("/Users/arpitsaxena683/") and not os.path.exists("/Users/arpitsaxena683"):
        if os.path.exists("/Users/arpitsaxena683gmail.com"):
            expanded = expanded.replace("/Users/arpitsaxena683/", "/Users/arpitsaxena683gmail.com/")

    # Resolve relative paths against workspace root
    if not os.path.isabs(expanded):
        expanded = os.path.join(workspace_root, expanded)
        
    abs_path = os.path.abspath(expanded)
    
    # If creating a new project and path is a generic directory (like Desktop or untitled folder), nest inside a timestamped subfolder
    if add_timestamp:
        abs_path = os.path.join(abs_path, f"{safe_title}_{ts_suffix}")

    try:
        os.makedirs(abs_path, exist_ok=True)
    except Exception:
        abs_path = os.path.join(workspace_root, "generated_projects", f"{safe_title}_{ts_suffix}")
        os.makedirs(abs_path, exist_ok=True)
        
    return abs_path

def create_project(title: str, description: str, goal: str, user_id: str, storage_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cfg_json = json.dumps(config or {})
    
    # Always assign a distinct timestamped directory for complete project isolation
    resolved_storage_path = sanitize_storage_path(storage_path, title, add_timestamp=True)

    cursor.execute(
        """
        INSERT INTO projects (id, title, description, storage_path, user_id, status, goal, config, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, title, description, resolved_storage_path, user_id, "created", goal, cfg_json, now, now)
    )
    conn.commit()
    conn.close()
    return {
        "id": project_id,
        "title": title,
        "description": description,
        "storage_path": resolved_storage_path,
        "user_id": user_id,
        "status": "created",
        "goal": goal,
        "config": config or {},
        "created_at": now,
        "updated_at": now
    }

def update_project(project_id: str, updates: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in updates.items():
        fields.append(f"{k} = ?")
        if isinstance(v, (dict, list)):
            values.append(json.dumps(v))
        else:
            values.append(v)
    fields.append("updated_at = ?")
    values.append(datetime.utcnow().isoformat())
    values.append(project_id)
    
    query = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

def delete_project(project_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subtasks WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM meeting_logs WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

# Subtasks Helpers
def create_subtask(project_id: str, title: str, description: str, worker_type: str, dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    subtask_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    deps_json = json.dumps(dependencies or [])
    cursor.execute(
        """
        INSERT INTO subtasks (id, project_id, title, description, worker_type, status, dependencies, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (subtask_id, project_id, title, description, worker_type, "pending", deps_json, now)
    )
    conn.commit()
    conn.close()
    return {
        "id": subtask_id,
        "project_id": project_id,
        "title": title,
        "description": description,
        "worker_type": worker_type,
        "status": "pending",
        "dependencies": dependencies or [],
        "created_at": now
    }

def get_project_subtasks(project_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subtasks WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("dependencies"):
            try: d["dependencies"] = json.loads(d["dependencies"])
            except: d["dependencies"] = []
        result.append(d)
    return result

def update_subtask(subtask_id: str, updates: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in updates.items():
        fields.append(f"{k} = ?")
        if isinstance(v, (dict, list)):
            values.append(json.dumps(v))
        else:
            values.append(v)
    values.append(subtask_id)
    query = f"UPDATE subtasks SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()

# Meeting Log Helpers
def add_meeting_log(project_id: str, sender: str, role: str, content: str, message_type: str = "chat", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    log_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    meta_json = json.dumps(metadata or {})
    cursor.execute(
        """
        INSERT INTO meeting_logs (id, project_id, sender, role, message_type, content, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (log_id, project_id, sender, role, message_type, content, meta_json, now)
    )
    conn.commit()
    conn.close()
    return {
        "id": log_id,
        "project_id": project_id,
        "sender": sender,
        "role": role,
        "message_type": message_type,
        "content": content,
        "metadata": metadata or {},
        "timestamp": now
    }

def get_project_meeting_logs(project_id: str) -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meeting_logs WHERE project_id = ? ORDER BY timestamp ASC", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("metadata"):
            try: d["metadata"] = json.loads(d["metadata"])
            except: pass
        result.append(d)
    return result
