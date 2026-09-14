import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional
from ..services.meeting_room import meeting_hub
from ..services.model_broker import model_broker
from ..database import update_subtask

class BaseWorkerAgent:
    def __init__(self, name: str, role: str, avatar: str, worker_type: str):
        self.name = name
        self.role = role
        self.avatar = avatar
        self.worker_type = worker_type

    async def execute_subtask(
        self,
        project_id: str,
        subtask: Dict[str, Any],
        project_goal: str,
        provider: str = "gemini",
        custom_keys: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        subtask_id = subtask["id"]
        title = subtask["title"]
        description = subtask["description"]
        start_ts = datetime.utcnow().isoformat()
        start_perf = time.perf_counter()

        # 1. Update subtask and agent status to working
        update_subtask(subtask_id, {"status": "in_progress", "assigned_to": self.name})
        meeting_hub.update_agent_status(project_id, self.name, "active", f"Working on: {title}")
        
        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=f"{self.avatar} **Started**: *{title}*\n\n> {description}",
            message_type="status",
            metadata={
                "subtask_id": subtask_id,
                "status": "in_progress",
                "start_time": start_ts,
                "worker_type": self.worker_type
            }
        )

        # 2. Build system prompt and context messages
        context_str = ""
        if context:
            context_str = "\n\nShared Project Context & Sibling Deliverables:\n" + "\n".join(
                [f"--- {k.upper()} ---\n{v}" for k, v in context.items() if v]
            )

        system_prompt = (
            f"You are the {self.name} ({self.role}).\n"
            f"Your responsibility is to build the '{self.worker_type}' module for project: '{project_goal}'.\n"
            f"Provide clean, modern, production-grade source code and markdown documentation.\n"
            f"Use code fences (e.g. ```html, ```javascript, ```css, ```python, ```sql) for all code."
        )

        messages = [
            {
                "role": "user",
                "content": f"Subtask: {title}\nDetails: {description}\nProject Goal: {project_goal}{context_str}"
            }
        ]

        # 3. Simulate thought & call Model Broker
        await asyncio.sleep(0.4)
        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=f"⚙️ Generating modular implementation for **{title}**...",
            message_type="thought",
            metadata={"subtask_id": subtask_id}
        )

        try:
            response = await model_broker.generate_response(
                provider=provider,
                system_prompt=system_prompt,
                messages=messages,
                custom_keys=custom_keys
            )
            output_content = response.get("content", "Completed.")
            provider_used = response.get("provider", provider)
            model_used = response.get("model", "default")
        except Exception as e:
            output_content = f"Error during execution: {str(e)}"
            provider_used = "error"
            model_used = "none"

        end_perf = time.perf_counter()
        end_ts = datetime.utcnow().isoformat()
        duration = round(end_perf - start_perf, 3)

        # 4. Mark subtask completed
        update_subtask(subtask_id, {
            "status": "completed",
            "output": output_content
        })
        meeting_hub.update_agent_status(project_id, self.name, "idle", f"Completed in {duration}s")

        # 5. Post deliverable back to Meeting Room
        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=f"✅ **{self.name}**: Completed *{title}* in {duration}s\n\n{output_content[:400]}...",
            message_type="deliverable",
            metadata={
                "subtask_id": subtask_id,
                "status": "completed",
                "provider": provider_used,
                "model": model_used,
                "start_time": start_ts,
                "end_time": end_ts,
                "duration_seconds": duration
            }
        )

        return {
            "subtask_id": subtask_id,
            "title": title,
            "worker": self.name,
            "worker_type": self.worker_type,
            "output": output_content,
            "provider": provider_used,
            "model": model_used,
            "start_time": start_ts,
            "end_time": end_ts,
            "duration_seconds": duration
        }


class FrontendWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="FrontendAgent",
            role="Frontend & UI/UX Specialist",
            avatar="🎨",
            worker_type="frontend"
        )


class BackendWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="BackendAgent",
            role="Backend & API Architect",
            avatar="⚡",
            worker_type="backend"
        )


class DatabaseWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="DatabaseAgent",
            role="Database Schema & Data Model Specialist",
            avatar="🗄️",
            worker_type="database"
        )


class IntegrationWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="IntegrationAgent",
            role="System Integration & Contract Reconciliation Lead",
            avatar="🔗",
            worker_type="integration"
        )


class TestingWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="TestingAgent",
            role="QA & Test Automation Specialist",
            avatar="🧪",
            worker_type="testing"
        )


class DocumentationWorker(BaseWorkerAgent):
    def __init__(self):
        super().__init__(
            name="DocumentationAgent",
            role="Technical Documentation & Developer Relations",
            avatar="📝",
            worker_type="documentation"
        )


def get_worker_pool() -> Dict[str, BaseWorkerAgent]:
    fe = FrontendWorker()
    be = BackendWorker()
    db = DatabaseWorker()
    integ = IntegrationWorker()
    test = TestingWorker()
    doc = DocumentationWorker()

    return {
        "frontend": fe,
        "backend": be,
        "database": db,
        "integration": integ,
        "testing": test,
        "documentation": doc,
        # Aliases for backward compatibility
        "coding": fe,
        "research": db
    }
