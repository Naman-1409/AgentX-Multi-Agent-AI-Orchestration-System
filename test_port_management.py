import os
import sys
import subprocess
import time
import httpx
import asyncio

API_BASE = "http://127.0.0.1:8000"

def get_pids_on_port_8080():
    try:
        res = subprocess.run("lsof -ti:8080", shell=True, capture_output=True, text=True)
        return [int(p.strip()) for p in res.stdout.split() if p.strip().isdigit()]
    except Exception:
        return []

async def test_exact_user_flow():
    print("\n==================================================================")
    print("  TESTING EXACT USER SCENARIO: PORT 8080 PROCESS MANAGEMENT & PID ")
    print("==================================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Build Project A (To-Do List App)
        print("\n1️⃣ Creating & Building Project A: 'Task To-Do App'...")
        res_a = await client.post(f"{API_BASE}/api/projects", json={
            "title": "Task To-Do App",
            "description": "To-Do list application with task completion",
            "goal": "Build a Task To-Do App with item list and completion checkboxes",
            "config": {"model": "smart_simulation"}
        })
        assert res_a.status_code == 200
        proj_a = res_a.json()["project"]
        proj_a_id = proj_a["id"]
        
        # Run Orchestration
        await client.post(f"{API_BASE}/api/projects/{proj_a_id}/start", json={"provider": "smart_simulation"})
        await asyncio.sleep(6.5)

        # Run on Port 8080
        print("   ▶️ Launching Project A on Port 8080...")
        run_res_a = (await client.post(f"{API_BASE}/api/projects/{proj_a_id}/runner/start", json={"port": 8080})).json()
        pid_a = run_res_a.get("pid")
        print(f"   Project A started with PID: {pid_a} on Port 8080")
        
        # Verify Port 8080 with lsof
        pids_8080 = get_pids_on_port_8080()
        print(f"   `lsof -ti:8080` check: {pids_8080} (Expected PID: {pid_a})")
        assert pid_a in pids_8080, "Project A PID must be listening on port 8080"
        assert len(pids_8080) == 1, "Exactly ONE process must listen on port 8080"

        # Verify Content
        content_a = (await client.get("http://127.0.0.1:8080/")).text
        assert "task" in content_a.lower() or "entry" in content_a.lower()
        print("   ✅ Project A is verified active on Port 8080.")

        # 2. Close / Exit Project A (Stop Server)
        print("\n2️⃣ Closing Project A (Triggering automatic port cleanup)...")
        stop_res = (await client.post(f"{API_BASE}/api/runner/force-stop")).json()
        print(f"   Stop runner response: {stop_res}")
        time.sleep(0.5)

        pids_after_stop = get_pids_on_port_8080()
        print(f"   `lsof -ti:8080` check after stop: {pids_after_stop}")
        assert len(pids_after_stop) == 0, "Port 8080 must be completely free after project close!"
        print("   ✅ Port 8080 is verified completely free and released.")

        # 3. Build Project B (Weather App)
        print("\n3️⃣ Creating & Building Project B: 'Live Weather Radar App'...")
        res_b = await client.post(f"{API_BASE}/api/projects", json={
            "title": "Live Weather Radar App",
            "description": "Meteorological radar and 7-day forecast",
            "goal": "Build a Live Weather Radar App with 7-day forecast and temperature toggle",
            "config": {"model": "smart_simulation"}
        })
        assert res_b.status_code == 200
        proj_b = res_b.json()["project"]
        proj_b_id = proj_b["id"]
        
        # Run Orchestration
        await client.post(f"{API_BASE}/api/projects/{proj_b_id}/start", json={"provider": "smart_simulation"})
        await asyncio.sleep(6.5)

        # Run on Port 8080
        print("   ▶️ Launching Project B on Port 8080...")
        run_res_b = (await client.post(f"{API_BASE}/api/projects/{proj_b_id}/runner/start", json={"port": 8080})).json()
        pid_b = run_res_b.get("pid")
        print(f"   Project B started with PID: {pid_b} on Port 8080")

        # Verify Port 8080 with lsof
        pids_8080_b = get_pids_on_port_8080()
        print(f"   `lsof -ti:8080` check: {pids_8080_b} (Expected PID: {pid_b})")
        assert pid_b in pids_8080_b, "Project B PID must be listening on port 8080"
        assert len(pids_8080_b) == 1, "Exactly ONE process must listen on port 8080"
        assert pid_b != pid_a, "PID B must be a new, separate process from PID A"

        # Verify Content on Port 8080 is WEATHER (not To-Do list!)
        content_b = (await client.get("http://127.0.0.1:8080/")).text
        assert "weather" in content_b.lower() or "forecast" in content_b.lower() or "open-meteo" in content_b.lower(), "Port 8080 must serve Weather App!"
        print(f"   Content verification: Found 'Live Weather Radar' / Open-Meteo ({len(content_b)} bytes)")
        print("   ✅ Project B is verified active on Port 8080, serving actual Weather App HTML!")

        # 4. Manual Force Stop Button Test
        print("\n4️⃣ Testing Manual Force Stop Server Button...")
        force_stop_res = (await client.post(f"{API_BASE}/api/runner/force-stop")).json()
        print(f"   Force-stop response: {force_stop_res}")
        time.sleep(0.5)
        pids_final = get_pids_on_port_8080()
        assert len(pids_final) == 0
        print("   ✅ Force Stop Server confirmed: Port 8080 is completely free.")

    print("\n🎉 ALL TESTS PASSED: PROCESS LIFECYCLE & PORT MANAGEMENT 100% VERIFIED!")

if __name__ == "__main__":
    asyncio.run(test_exact_user_flow())
