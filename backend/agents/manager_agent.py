import os
import asyncio
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..database import (
    get_project, update_project, create_subtask, get_project_subtasks, add_meeting_log, sanitize_storage_path
)
from ..services.meeting_room import meeting_hub
from ..services.model_broker import model_broker
from .worker_agents import get_worker_pool

class ManagerAgent:
    def __init__(self):
        self.name = "ManagerAgent"
        self.role = "Project Orchestrator & Multi-Agent Lead"
        self.avatar = "👔"

    async def handle_human_message(self, project_id: str, human_sender: str, message: str):
        """
        Actively responds to human chat messages in real time.
        If the message contains an instruction or build request, initiates or updates orchestration.
        """
        meeting_hub.update_agent_status(project_id, self.name, "active", "Replying to team instruction")
        
        project = get_project(project_id)
        project_goal = (project.get("goal") if project else "") or message
        provider = (project.get("config", {}).get("model") if project else "gemini") or "gemini"

        response = await model_broker.generate_response(
            provider=provider,
            system_prompt=(
                f"You are the Manager Agent for project '{project_goal}'.\n"
                f"A team member named {human_sender} sent: '{message}'.\n"
                f"Respond as the Manager Agent in a helpful, collaborative, proactive manner."
            ),
            messages=[{"role": "user", "content": message}]
        )
        
        reply_content = response.get("content", f"Received your message: {message}")
        
        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=reply_content,
            message_type="chat"
        )
        
        meeting_hub.update_agent_status(project_id, self.name, "idle", "Ready")

        build_keywords = ["create", "build", "make", "develop", "generate", "start", "run", "do it"]
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in build_keywords) and len(message.split()) >= 3:
            if project and project.get("status") != "in_progress":
                update_project(project_id, {"goal": message})
                asyncio.create_task(self.run_project_orchestration(project_id=project_id, provider=provider))

    async def run_project_orchestration(
        self,
        project_id: str,
        provider: str = "gemini",
        custom_keys: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Main Multi-Agent Orchestration Flow:
        Stage 1 (Parallel): Database + Frontend + Backend execute concurrently via asyncio.gather
        Stage 2 (Sequential): Integration Agent reconciles contracts & connects UI to API
        Stage 3 (Parallel): Testing Agent + Documentation Agent execute concurrently
        """
        overall_start_perf = time.perf_counter()
        overall_start_ts = datetime.utcnow().isoformat()

        project = get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project_goal = project.get("goal") or project.get("title", "")
        storage_path = sanitize_storage_path(project.get("storage_path"), project.get("title", "app"))

        # 1. Start Meeting Room Session
        update_project(project_id, {"status": "in_progress"})
        meeting_hub.set_room_progress(project_id, 10, "Requirement Extraction & Task Decomposition")
        meeting_hub.update_agent_status(project_id, self.name, "active", "Decomposing requirements into DAG stages")

        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=(
                f"👋 **Multi-Agent Meeting Room Session Started**\n\n"
                f"**Target Goal:** {project_goal}\n"
                f"**Target Directory:** `{storage_path}`\n\n"
                f"Decomposing project into specialized modules for parallel agent execution..."
            ),
            message_type="announcement"
        )

        # 2. Decompose into structured DAG stages
        subtasks_plan = self._decompose_goal(project_goal)
        meeting_hub.set_room_progress(project_id, 25, "Agent Roles Assigned")

        # 3. Create subtasks in database
        created_subtasks_by_type = {}
        all_created_subtasks = []
        for task_def in subtasks_plan:
            st = create_subtask(
                project_id=project_id,
                title=task_def["title"],
                description=task_def["description"],
                worker_type=task_def["worker_type"],
                dependencies=task_def.get("dependencies", [])
            )
            created_subtasks_by_type[task_def["worker_type"]] = st
            all_created_subtasks.append(st)

        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=(
                f"📋 **Task Breakdown & Multi-Agent Assignment Complete**:\n\n"
                f"**Stage 1 (Parallel Independent Execution)**:\n"
                f"- 🗄️ `DatabaseAgent`: {created_subtasks_by_type['database']['title']}\n"
                f"- 🎨 `FrontendAgent`: {created_subtasks_by_type['frontend']['title']}\n"
                f"- ⚡ `BackendAgent`: {created_subtasks_by_type['backend']['title']}\n\n"
                f"**Stage 2 (Contract Integration & Reconciliation)**:\n"
                f"- 🔗 `IntegrationAgent`: {created_subtasks_by_type['integration']['title']}\n\n"
                f"**Stage 3 (Verification & Documentation)**:\n"
                f"- 🧪 `TestingAgent`: {created_subtasks_by_type['testing']['title']}\n"
                f"- 📝 `DocumentationAgent`: {created_subtasks_by_type['documentation']['title']}\n\n"
                f"🚀 *Launching Stage 1 workers concurrently now...*"
            ),
            message_type="plan",
            metadata={"subtasks": all_created_subtasks}
        )

        worker_pool = get_worker_pool()
        all_worker_results = []
        shared_context = {}

        # ==========================================
        # STAGE 1: Parallel Execution (DB, Frontend, Backend)
        # ==========================================
        meeting_hub.set_room_progress(project_id, 40, "Stage 1: Concurrent Parallel Execution")
        stage1_tasks = [
            worker_pool["database"].execute_subtask(
                project_id, created_subtasks_by_type["database"], project_goal, provider, custom_keys
            ),
            worker_pool["frontend"].execute_subtask(
                project_id, created_subtasks_by_type["frontend"], project_goal, provider, custom_keys
            ),
            worker_pool["backend"].execute_subtask(
                project_id, created_subtasks_by_type["backend"], project_goal, provider, custom_keys
            )
        ]

        stage1_results = await asyncio.gather(*stage1_tasks, return_exceptions=True)
        for i, res in enumerate(stage1_results):
            if isinstance(res, Exception):
                w_type = ["database", "frontend", "backend"][i]
                all_worker_results.append({
                    "subtask_id": created_subtasks_by_type[w_type]["id"],
                    "title": created_subtasks_by_type[w_type]["title"],
                    "worker": f"{w_type.capitalize()}Agent",
                    "worker_type": w_type,
                    "output": f"Worker Exception: {str(res)}",
                    "status": "error"
                })
            else:
                all_worker_results.append(res)
                shared_context[res["worker_type"]] = res.get("output", "")

        # ==========================================
        # STAGE 2: Integration & Contract Reconciliation
        # ==========================================
        meeting_hub.set_room_progress(project_id, 70, "Stage 2: Integration & Wireup")
        meeting_hub.update_agent_status(project_id, "IntegrationAgent", "active", "Reconciling contracts & connecting UI to API")

        integration_res = await worker_pool["integration"].execute_subtask(
            project_id=project_id,
            subtask=created_subtasks_by_type["integration"],
            project_goal=project_goal,
            provider=provider,
            custom_keys=custom_keys,
            context=shared_context
        )
        all_worker_results.append(integration_res)
        shared_context["integration"] = integration_res.get("output", "")

        # ==========================================
        # STAGE 3: Parallel Verification & Docs (Testing + Documentation)
        # ==========================================
        meeting_hub.set_room_progress(project_id, 85, "Stage 3: Testing & Documentation")
        stage3_tasks = [
            worker_pool["testing"].execute_subtask(
                project_id, created_subtasks_by_type["testing"], project_goal, provider, custom_keys, context=shared_context
            ),
            worker_pool["documentation"].execute_subtask(
                project_id, created_subtasks_by_type["documentation"], project_goal, provider, custom_keys, context=shared_context
            )
        ]
        stage3_results = await asyncio.gather(*stage3_tasks, return_exceptions=True)
        for i, res in enumerate(stage3_results):
            if isinstance(res, Exception):
                w_type = ["testing", "documentation"][i]
                all_worker_results.append({
                    "subtask_id": created_subtasks_by_type[w_type]["id"],
                    "title": created_subtasks_by_type[w_type]["title"],
                    "worker": f"{w_type.capitalize()}Agent",
                    "worker_type": w_type,
                    "output": f"Worker Exception: {str(res)}",
                    "status": "error"
                })
            else:
                all_worker_results.append(res)
                shared_context[res["worker_type"]] = res.get("output", "")

        # ==========================================
        # STEP 4: Merge, Reconciliation & Disk Write
        # ==========================================
        meeting_hub.set_room_progress(project_id, 92, "Merging Deliverables to Unified Folder")
        meeting_hub.update_agent_status(project_id, self.name, "active", "Consolidating project bundle")

        overall_end_perf = time.perf_counter()
        total_wall_clock = round(overall_end_perf - overall_start_perf, 3)
        
        # Calculate concurrency metrics
        individual_durations = [r.get("duration_seconds", 0) for r in all_worker_results if isinstance(r, dict)]
        sum_durations = round(sum(individual_durations), 3)
        speedup = round(sum_durations / total_wall_clock, 2) if total_wall_clock > 0 else 1.0

        final_deliverable = self._synthesize_deliverable(
            project_goal=project_goal,
            storage_path=storage_path,
            worker_results=all_worker_results,
            metrics={
                "wall_clock_seconds": total_wall_clock,
                "serial_sum_seconds": sum_durations,
                "concurrency_speedup": f"{speedup}x",
                "start_time": overall_start_ts,
                "end_time": datetime.utcnow().isoformat()
            }
        )

        saved_files = self._write_project_to_disk(storage_path, project_goal, final_deliverable)
        final_deliverable["saved_files"] = saved_files
        final_deliverable["storage_path"] = storage_path

        # 5. Finalize project
        update_project(project_id, {
            "status": "completed",
            "deliverable": final_deliverable,
            "storage_path": storage_path
        })
        meeting_hub.set_room_progress(project_id, 100, "Project Complete")
        meeting_hub.update_agent_status(project_id, self.name, "idle", "Published complete deliverable")

        files_list_md = "\n".join([f"- `{f}`" for f in saved_files])
        await meeting_hub.post_message(
            project_id=project_id,
            sender=self.name,
            role=self.role,
            content=(
                f"🎉 **Unified Multi-Agent Deliverable Complete!**\n\n"
                f"📁 **Project Folder:** `{storage_path}`\n\n"
                f"⚡ **Parallelism Metrics**:\n"
                f"- Total Wall-Clock Time: **{total_wall_clock}s** (vs {sum_durations}s serialized)\n"
                f"- Concurrency Speedup: **{speedup}x**\n\n"
                f"**Generated Files:**\n{files_list_md}\n\n"
                f"### Run Instructions:\n"
                f"1. Open `{storage_path}/index.html` in browser\n"
                f"2. Or start backend: `cd \"{storage_path}\" && python server.py`"
            ),
            message_type="synthesis",
            metadata={"deliverable": final_deliverable}
        )

        return {
            "project_id": project_id,
            "status": "completed",
            "deliverable": final_deliverable,
            "worker_results": all_worker_results,
            "metrics": final_deliverable.get("metrics", {})
        }

    def _decompose_goal(self, goal: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "Design Database Schema & Data Models",
                "description": f"Architect SQLite/SQL schema and data models for: '{goal}'.",
                "worker_type": "database",
                "dependencies": []
            },
            {
                "title": "Build Frontend UI Components & State Reactive Layer",
                "description": f"Create modern, glassmorphic UI, responsive layouts, and interactive client logic for: '{goal}'.",
                "worker_type": "frontend",
                "dependencies": []
            },
            {
                "title": "Implement FastAPI Backend REST Routes & Business Logic",
                "description": f"Build server endpoints, CRUD controllers, CORS handling, and storage interfaces for: '{goal}'.",
                "worker_type": "backend",
                "dependencies": []
            },
            {
                "title": "Reconcile Endpoint Contracts & Wire Frontend to Backend",
                "description": f"Connect UI fetch calls to backend REST routes, align JSON schemas, and ensure end-to-end integration for: '{goal}'.",
                "worker_type": "integration",
                "dependencies": ["database", "frontend", "backend"]
            },
            {
                "title": "Construct Automated QA & Boundary Test Suite",
                "description": f"Generate automated unit and integration tests to validate API routes and logic for: '{goal}'.",
                "worker_type": "testing",
                "dependencies": ["integration"]
            },
            {
                "title": "Generate Developer Setup Guide & README",
                "description": f"Write complete README with run instructions, architecture summary, and agent contribution breakdown for: '{goal}'.",
                "worker_type": "documentation",
                "dependencies": ["integration"]
            }
        ]

    def _synthesize_deliverable(
        self,
        project_goal: str,
        storage_path: str,
        worker_results: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        db_out = next((r["output"] for r in worker_results if r.get("worker_type") == "database"), "")
        fe_out = next((r["output"] for r in worker_results if r.get("worker_type") == "frontend"), "")
        be_out = next((r["output"] for r in worker_results if r.get("worker_type") == "backend"), "")
        integ_out = next((r["output"] for r in worker_results if r.get("worker_type") == "integration"), "")
        test_out = next((r["output"] for r in worker_results if r.get("worker_type") == "testing"), "")
        doc_out = next((r["output"] for r in worker_results if r.get("worker_type") == "documentation"), "")

        return {
            "title": f"Deliverable: {project_goal}",
            "summary": f"Unified Multi-Agent Full-Stack Application for '{project_goal}'.",
            "storage_path": storage_path,
            "metrics": metrics,
            "database": db_out,
            "frontend": fe_out,
            "backend": be_out,
            "integration": integ_out,
            "tests": test_out,
            "docs": doc_out,
            "agents_involved": [
                "ManagerAgent", "DatabaseAgent", "FrontendAgent",
                "BackendAgent", "IntegrationAgent", "TestingAgent", "DocumentationAgent"
            ],
            "agent_timings": [
                {
                    "worker": r.get("worker", "Agent"),
                    "type": r.get("worker_type", "worker"),
                    "duration_s": r.get("duration_seconds", 0),
                    "start": r.get("start_time", ""),
                    "end": r.get("end_time", "")
                }
                for r in worker_results if isinstance(r, dict)
            ]
        }

    def _write_project_to_disk(self, storage_path: str, project_goal: str, deliverable: Dict[str, Any]) -> List[str]:
        try:
            os.makedirs(storage_path, exist_ok=True)
        except Exception:
            workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            safe_slug = "".join(c if c.isalnum() else "_" for c in project_goal[:25].lower()).strip("_") or "app"
            storage_path = os.path.join(workspace_root, "generated_projects", safe_slug)
            os.makedirs(storage_path, exist_ok=True)
            deliverable["storage_path"] = storage_path
        saved = []

        # 1. Frontend Files (HTML, CSS, JS)
        fe_text = deliverable.get("frontend", "")
        code_blocks = self._extract_all_code_blocks(fe_text)
        
        html_code = code_blocks.get("html")
        if html_code:
            html_path = os.path.join(storage_path, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_code)
            saved.append("index.html")
        else:
            # Fallback index.html
            html_path = os.path.join(storage_path, "index.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(f"<!DOCTYPE html><html><head><title>{project_goal}</title></head><body><h1>{project_goal}</h1></body></html>")
            saved.append("index.html")

        css_code = code_blocks.get("css")
        if css_code:
            css_path = os.path.join(storage_path, "styles.css")
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css_code)
            saved.append("styles.css")

        js_code = code_blocks.get("javascript") or code_blocks.get("js")
        if js_code:
            js_path = os.path.join(storage_path, "app.js")
            with open(js_path, "w", encoding="utf-8") as f:
                f.write(js_code)
            saved.append("app.js")

        # 2. Backend Server File (server.py)
        be_text = deliverable.get("backend", "")
        be_blocks = self._extract_all_code_blocks(be_text)
        server_code = be_blocks.get("python") or be_blocks.get("py")
        if server_code:
            server_path = os.path.join(storage_path, "server.py")
            with open(server_path, "w", encoding="utf-8") as f:
                f.write(server_code)
            saved.append("server.py")

        # 3. Database Schema File (schema.sql)
        db_text = deliverable.get("database", "")
        db_blocks = self._extract_all_code_blocks(db_text)
        sql_code = db_blocks.get("sql")
        if sql_code:
            sql_path = os.path.join(storage_path, "schema.sql")
            with open(sql_path, "w", encoding="utf-8") as f:
                f.write(sql_code)
            saved.append("schema.sql")

        # 4. QA Test Suite (test_suite.py)
        test_text = deliverable.get("tests", "")
        test_blocks = self._extract_all_code_blocks(test_text)
        test_code = test_blocks.get("python") or test_blocks.get("py") or test_blocks.get("javascript")
        if test_code:
            test_ext = ".py" if ("import" in test_code or "def " in test_code) else ".js"
            test_path = os.path.join(storage_path, f"test_suite{test_ext}")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            saved.append(f"test_suite{test_ext}")

        # 5. README.md & Metrics
        doc_text = deliverable.get("docs", "")
        clean_doc = re.sub(r"```markdown|```", "", doc_text).strip()
        metrics = deliverable.get("metrics", {})
        metrics_table = (
            f"\n\n## ⚡ Multi-Agent Concurrency & Performance Metrics\n"
            f"- **Total Wall-Clock Time**: `{metrics.get('wall_clock_seconds', 0)}s`\n"
            f"- **Serialized Execution Sum**: `{metrics.get('serial_sum_seconds', 0)}s`\n"
            f"- **Concurrency Speedup**: `{metrics.get('concurrency_speedup', '1.0x')}`\n\n"
            f"### Agent Timings Breakdown:\n"
            f"| Agent Role | Subtask Module | Duration | Start Time |\n"
            f"| :--- | :--- | :--- | :--- |\n"
        )
        for t in deliverable.get("agent_timings", []):
            metrics_table += f"| `{t.get('worker')}` | {t.get('type')} | {t.get('duration_s')}s | `{t.get('start', '')[:19]}` |\n"

        readme_path = os.path.join(storage_path, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"{clean_doc}\n{metrics_table}")
        saved.append("README.md")

        # 6. multi_agent_metrics.json (Proof of Parallelism metadata)
        metrics_file = os.path.join(storage_path, "multi_agent_metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump({
                "project_goal": project_goal,
                "metrics": metrics,
                "agent_timings": deliverable.get("agent_timings", []),
                "saved_files": saved
            }, f, indent=2)
        saved.append("multi_agent_metrics.json")

        return saved

    def _extract_all_code_blocks(self, text: str) -> Dict[str, str]:
        blocks = {}
        matches = re.findall(r"```([a-zA-Z0-9_\-\+]*)\n([\s\S]*?)```", text)
        for lang, content in matches:
            l = lang.lower().strip() or "text"
            blocks[l] = content.strip()
        return blocks

manager_agent = ManagerAgent()
