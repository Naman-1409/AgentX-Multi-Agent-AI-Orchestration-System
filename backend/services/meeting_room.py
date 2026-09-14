import asyncio
import json
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from ..database import add_meeting_log, get_project_meeting_logs

class MeetingRoomHub:
    def __init__(self):
        # project_id -> list of asyncio.Queue for live streaming subscribers (SSE / WebSocket)
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        # project_id -> dict of active participants and their current status
        self.active_rooms: Dict[str, Dict[str, Any]] = {}

    def get_room_state(self, project_id: str) -> Dict[str, Any]:
        if project_id not in self.active_rooms:
            self.active_rooms[project_id] = {
                "status": "idle",
                "agents": {
                    "ManagerAgent": {"role": "Project Orchestrator & Synthesis Lead", "status": "idle", "avatar": "👔"},
                    "FrontendAgent": {"role": "Frontend & UI/UX Specialist", "status": "idle", "avatar": "🎨"},
                    "BackendAgent": {"role": "Backend & API Architect", "status": "idle", "avatar": "⚡"},
                    "DatabaseAgent": {"role": "Database Schema & Data Models", "status": "idle", "avatar": "🗄️"},
                    "IntegrationAgent": {"role": "Contract Reconciliation & Integration", "status": "idle", "avatar": "🔗"},
                    "TestingAgent": {"role": "QA, Validation & Test Cases", "status": "idle", "avatar": "🧪"},
                    "DocumentationAgent": {"role": "Technical Documentation & Setup", "status": "idle", "avatar": "📝"}
                },
                "current_task": None,
                "progress": 0
            }
        return self.active_rooms[project_id]

    def update_agent_status(self, project_id: str, agent_name: str, status: str, current_activity: Optional[str] = None):
        room = self.get_room_state(project_id)
        if agent_name in room["agents"]:
            room["agents"][agent_name]["status"] = status
            if current_activity:
                room["agents"][agent_name]["activity"] = current_activity
        elif agent_name == "Manager":
            room["agents"]["ManagerAgent"]["status"] = status
            if current_activity:
                room["agents"]["ManagerAgent"]["activity"] = current_activity
        
        # Broadcast status update
        asyncio.create_task(self.broadcast(project_id, {
            "type": "agent_status_change",
            "agent": agent_name,
            "status": status,
            "activity": current_activity,
            "room_state": room,
            "timestamp": datetime.utcnow().isoformat()
        }))

    def set_room_progress(self, project_id: str, progress: int, status: Optional[str] = None):
        room = self.get_room_state(project_id)
        room["progress"] = progress
        if status:
            room["status"] = status
        asyncio.create_task(self.broadcast(project_id, {
            "type": "progress_update",
            "progress": progress,
            "status": room["status"],
            "timestamp": datetime.utcnow().isoformat()
        }))

    async def post_message(
        self,
        project_id: str,
        sender: str,
        role: str,
        content: str,
        message_type: str = "chat",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Persist in DB
        log_entry = add_meeting_log(
            project_id=project_id,
            sender=sender,
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata
        )
        
        # Broadcast to all live listeners
        event = {
            "type": "message",
            "data": log_entry
        }
        await self.broadcast(project_id, event)
        return log_entry

    async def broadcast(self, project_id: str, event: Dict[str, Any]):
        if project_id in self.subscribers:
            dead_queues = set()
            for q in list(self.subscribers[project_id]):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead_queues.add(q)
                except Exception:
                    dead_queues.add(q)
            self.subscribers[project_id] -= dead_queues

    def subscribe(self, project_id: str) -> asyncio.Queue:
        if project_id not in self.subscribers:
            self.subscribers[project_id] = set()
        q = asyncio.Queue(maxsize=100)
        self.subscribers[project_id].add(q)
        return q

    def unsubscribe(self, project_id: str, q: asyncio.Queue):
        if project_id in self.subscribers and q in self.subscribers[project_id]:
            self.subscribers[project_id].remove(q)

meeting_hub = MeetingRoomHub()
