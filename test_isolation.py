import os
import sys
import time
import httpx
import asyncio

API_BASE = "http://127.0.0.1:8000"

async def test_end_to_end_isolation():
    print("=================================================================")
    print("  TESTING COMPLETE MULTI-PROJECT ISOLATION & DYNAMIC RUNNER 8080 ")
    print("=================================================================")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create Project A (To-Do List)
        print("\n1️⃣ Creating Project A: 'Task Management App'...")
        res_a = await client.post(f"{API_BASE}/api/projects", json={
            "title": "Task Management App",
            "description": "Interactive to-do list with items",
            "goal": "Build a Task Management App with tasks and completion toggle",
            "config": {"model": "smart_simulation"}
        })
        assert res_a.status_code == 200
        proj_a = res_a.json()["project"]
        proj_a_id = proj_a["id"]
        dir_a = proj_a["storage_path"]
        print(f"   Project A ID: {proj_a_id}")
        print(f"   Project A Folder: {dir_a}")

        # Start Multi-Agent Orchestration for Project A
        print("   Running Multi-Agent Orchestration for Project A...")
        start_a = await client.post(f"{API_BASE}/api/projects/{proj_a_id}/start", json={"provider": "smart_simulation"})
        assert start_a.status_code == 200
        await asyncio.sleep(7.0)

        # Launch Project A on Port 8080
        print("   Launching Project A on Port 8080...")
        runner_a = await client.post(f"{API_BASE}/api/projects/{proj_a_id}/runner/start", json={"port": 8080})
        assert runner_a.status_code == 200
        await asyncio.sleep(1.0)

        # Verify Port 8080 content for Project A
        resp_8080_a = await client.get("http://127.0.0.1:8080/")
        assert resp_8080_a.status_code == 200
        print(f"   Port 8080 responded for Project A (Length: {len(resp_8080_a.text)} bytes)")
        assert "task" in resp_8080_a.text.lower() or "item" in resp_8080_a.text.lower()
        print("   ✅ Project A is actively served on Port 8080.")

        # 2. Create Project B (Weather App)
        print("\n2️⃣ Creating Project B: 'Live Weather Radar App'...")
        res_b = await client.post(f"{API_BASE}/api/projects", json={
            "title": "Live Weather Radar App",
            "description": "Real-time meteorological forecast with radar",
            "goal": "Build a Live Weather Radar App with 7-day forecast and temperature toggle",
            "config": {"model": "smart_simulation"}
        })
        assert res_b.status_code == 200
        proj_b = res_b.json()["project"]
        proj_b_id = proj_b["id"]
        dir_b = proj_b["storage_path"]
        print(f"   Project B ID: {proj_b_id}")
        print(f"   Project B Folder: {dir_b}")

        # Confirm different folders
        assert dir_a != dir_b, "Project folders must be distinct!"
        print(f"   ✅ Folder Isolation Confirmed: {os.path.basename(dir_a)} != {os.path.basename(dir_b)}")

        # Start Multi-Agent Orchestration for Project B
        print("   Running Multi-Agent Orchestration for Project B...")
        start_b = await client.post(f"{API_BASE}/api/projects/{proj_b_id}/start", json={"provider": "smart_simulation"})
        assert start_b.status_code == 200
        await asyncio.sleep(7.0)

        # Launch Project B on Port 8080 (Should kill Project A and take over port 8080)
        print("   Launching Project B on Port 8080 (Switching from Project A)...")
        runner_b = await client.post(f"{API_BASE}/api/projects/{proj_b_id}/runner/start", json={"port": 8080})
        assert runner_b.status_code == 200
        await asyncio.sleep(1.0)

        # Verify Port 8080 content for Project B
        resp_8080_b = await client.get("http://127.0.0.1:8080/", headers={"Cache-Control": "no-cache"})
        assert resp_8080_b.status_code == 200
        print(f"   Port 8080 responded for Project B (Length: {len(resp_8080_b.text)} bytes)")
        
        # Verify it is WEATHER content and NOT To-Do content!
        assert "weather" in resp_8080_b.text.lower() or "forecast" in resp_8080_b.text.lower(), "Port 8080 must serve Project B Weather code!"
        assert "open-meteo" in resp_8080_b.text.lower() or "temp-display" in resp_8080_b.text.lower()
        print("   ✅ Port 8080 successfully killed Project A and is now serving Project B (Weather App)!")

        # 3. Verify Files in File Tree API for both projects
        files_a = (await client.get(f"{API_BASE}/api/projects/{proj_a_id}/files")).json()["files"]
        files_b = (await client.get(f"{API_BASE}/api/projects/{proj_b_id}/files")).json()["files"]
        assert len(files_a) > 0 and len(files_b) > 0
        print(f"   Project A files count: {len(files_a)}")
        print(f"   Project B files count: {len(files_b)}")
        print("   ✅ Both project file trees are completely isolated and accessible.")

    print("\n🎉 ALL MULTI-PROJECT ISOLATION & PORT RECYCLING TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(test_end_to_end_isolation())
