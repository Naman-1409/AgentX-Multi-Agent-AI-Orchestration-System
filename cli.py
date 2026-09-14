#!/usr/bin/env python3
"""
Multi-Agent Code Generation Platform - Interactive CLI
Orchestrates specialized parallel AI agents (Manager, Frontend, Backend, Database, Integration, QA, Docs)
"""
import os
import sys
import asyncio
import time
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database import init_db, create_project, get_db
from backend.agents.manager_agent import manager_agent
from backend.services.model_broker import model_broker

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def banner():
    print(f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════════════════╗
║        🤖 MULTI-AGENT PARALLEL CODE GENERATION PLATFORM         ║
║            Manager-Workers Collaborative Orchestrator            ║
╚══════════════════════════════════════════════════════════════════╝{RESET}
""")

async def run_cli():
    banner()
    init_db()

    # Step 1: User Input
    print(f"{YELLOW}STEP 1 — REQUIREMENT EXTRACTION{RESET}")
    print("Enter your project idea in plain language (or press Enter for default demo):")
    try:
        user_input = input(f"{BOLD}> {RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return

    if not user_input:
        user_input = "Build a real-time Task Management App with FastAPI REST API, modern glassmorphic UI, and SQLite persistence"

    print(f"\n{GREEN}✔ Project Requirement Received:{RESET} {BOLD}{user_input}{RESET}\n")

    # Step 2: Choose Provider
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    provider = "gemini" if gemini_key else "smart_simulation"
    provider_label = f"Google Gemini ({os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')})" if gemini_key else "Smart Multi-Agent Synthesizer (Zero-Key Offline Mode)"
    
    print(f"🤖 {DIM}LLM Provider:{RESET} {CYAN}{provider_label}{RESET}")
    print(f"📁 {DIM}Workspace Root:{RESET} {os.path.dirname(os.path.abspath(__file__))}")
    print("─" * 68)

    # Step 3: Create Project in Database
    title_slug = "".join(c if c.isalnum() else "_" for c in user_input[:30].lower()).strip("_")
    storage_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "generated_projects",
        title_slug
    )

    conn = get_db()
    admin_user = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
    user_id = admin_user["id"] if admin_user else "default_user"
    conn.close()

    proj = create_project(
        title=user_input[:50],
        description=user_input,
        goal=user_input,
        user_id=user_id,
        storage_path=storage_path,
        config={"model": provider}
    )
    project_id = proj["id"]

    print(f"\n{MAGENTA}STEP 2 — TASK BREAKDOWN & AGENT ASSIGNMENT{RESET}")
    print(f"👔 {BOLD}Manager Agent:{RESET} Analyzing prompt and constructing 3-stage dependency DAG...")
    await asyncio.sleep(0.5)

    print(f"  ├─ 🗄️  {BOLD}Database Agent{RESET}     → Design SQLite relational schema & data models")
    print(f"  ├─ 🎨 {BOLD}Frontend Agent{RESET}     → Build responsive glassmorphic UI, components & styling")
    print(f"  ├─ ⚡ {BOLD}Backend Agent{RESET}      → Build FastAPI server, REST CRUD endpoints & CORS")
    print(f"  ├─ 🔗 {BOLD}Integration Agent{RESET}  → Reconcile endpoint contracts & wire frontend to API")
    print(f"  ├─ 🧪 {BOLD}Testing Agent{RESET}      → Generate automated QA test suite & boundary checks")
    print(f"  └─ 📝 {BOLD}Documentation Agent{RESET}→ Compile README, architecture diagrams & run instructions\n")

    print(f"{YELLOW}STEP 3 — PARALLEL EXECUTION WITH LIVE BENCHMARKS{RESET}")
    print(f"🚀 {CYAN}Launching Stage 1 (Database, Frontend, Backend) concurrently in parallel...{RESET}\n")

    t0 = time.perf_counter()
    result = await manager_agent.run_project_orchestration(
        project_id=project_id,
        provider=provider
    )
    t1 = time.perf_counter()

    worker_results = result.get("worker_results", [])
    metrics = result.get("deliverable", {}).get("metrics", {})
    saved_files = result.get("deliverable", {}).get("saved_files", [])

    # Print Live Agent Status Summary
    for wr in worker_results:
        w_name = wr.get("worker", "Agent")
        w_type = wr.get("worker_type", "")
        duration = wr.get("duration_seconds", 0)
        start = wr.get("start_time", "")[11:23]
        end = wr.get("end_time", "")[11:23]
        print(f"  ✅ {GREEN}{BOLD}{w_name}{RESET} ({w_type}): Completed in {duration}s  {DIM}[{start} → {end}]{RESET}")

    # Step 4 & 5: Summary & Delivery
    print(f"\n{MAGENTA}STEP 4 & 5 — COORDINATION, MERGE & FINAL DELIVERY{RESET}")
    print(f"📁 {BOLD}Generated Output Folder:{RESET} {CYAN}{storage_path}{RESET}")
    print(f"\n{BOLD}Files Created in Project:{RESET}")
    for f in saved_files:
        print(f"  📄 {GREEN}{f}{RESET}")

    print(f"\n{BOLD}⚡ Concurrency Performance Proof:{RESET}")
    print(f"  • Total Wall-Clock Time : {CYAN}{BOLD}{metrics.get('wall_clock_seconds', round(t1-t0, 3))}s{RESET}")
    print(f"  • Sum of Serialized Work: {YELLOW}{metrics.get('serial_sum_seconds', 0)}s{RESET}")
    print(f"  • Parallelism Factor    : {GREEN}{BOLD}{metrics.get('concurrency_speedup', '1.0x')} faster{RESET}")

    print(f"\n{BOLD}🚀 Run Instructions:{RESET}")
    print(f"  1. Web Browser Direct:  open \"{storage_path}/index.html\"")
    print(f"  2. FastAPI Full-Stack:  cd \"{storage_path}\" && python server.py")
    print(f"  3. Run Automated Tests: cd \"{storage_path}\" && python test_suite.py\n")

if __name__ == "__main__":
    asyncio.run(run_cli())
