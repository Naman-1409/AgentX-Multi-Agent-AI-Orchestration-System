import os
import sys
import subprocess
import time
import socket
import signal
import threading
from typing import Dict, Any, Optional

class DedicatedProcessSandboxRunner:
    """
    Manages isolated project execution using dedicated OS subprocesses.
    Explicitly tracks process IDs (PIDs), kills stale/previous processes,
    and provides complete thread-safe lifecycle management (Start, Stop, Force-Kill).
    """
    def __init__(self, default_port: int = 8080):
        self.default_port = default_port
        self.active_port = default_port
        self.active_process: Optional[subprocess.Popen] = None
        self.active_pid: Optional[int] = None
        self.active_project_id: Optional[str] = None
        self.active_directory: Optional[str] = None
        self.lock = threading.Lock()
        self.logs = []

    def is_port_in_use(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def find_pids_on_port(self, port: int) -> list:
        try:
            cmd = f"lsof -ti:{port}"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            pids = [int(p.strip()) for p in res.stdout.split() if p.strip().isdigit()]
            return pids
        except Exception:
            return []

    def kill_port_processes(self, port: int) -> list:
        """
        Finds and forcefully terminates any process listening on the specified port.
        """
        killed_pids = []
        my_pid = os.getpid()
        pids = self.find_pids_on_port(port)

        for pid in pids:
            if pid != my_pid:
                try:
                    print(f"🛑 Port {port} was in use by process (PID: {pid}) — stopping it now...")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.15)
                    # If still alive, SIGKILL
                    os.kill(pid, signal.SIGKILL)
                    killed_pids.append(pid)
                    print(f"✅ Terminated process PID {pid} on port {port}")
                except ProcessLookupError:
                    pass
                except Exception as e:
                    print(f"⚠️ Error stopping PID {pid}: {str(e)}")

        time.sleep(0.25)
        return killed_pids

    def start_project_server(self, project_id: str, target_directory: str, port: Optional[int] = None) -> Dict[str, Any]:
        """
        Thread-safely:
        1. If already running this exact directory and process is alive, returns running status.
        2. Terminates existing active subprocess.
        3. Sweeps and kills any process occupying the port.
        4. Spawns an isolated subprocess for the target project directory.
        5. Stores the PID in state.
        """
        with self.lock:
            target_port = port or self.default_port
            target_directory = os.path.abspath(target_directory)
            os.makedirs(target_directory, exist_ok=True)
            project_name = os.path.basename(target_directory)

            # If already running this exact directory and process is healthy, return immediately
            if (self.active_process and self.active_process.poll() is None 
                and self.active_directory == target_directory 
                and self.active_port == target_port):
                return {
                    "status": "running",
                    "pid": self.active_pid,
                    "port": target_port,
                    "url": f"http://127.0.0.1:{target_port}",
                    "directory": target_directory,
                    "project_id": project_id
                }

            print(f"\n🔄 Preparing execution environment for [{project_name}] on port {target_port}...")

            # 1. Stop tracked previous subprocess if alive
            self._internal_stop()

            # 2. Check if port is in use by any orphan process and kill it
            killed = self.kill_port_processes(target_port)
            if killed:
                msg = f"Port {target_port} was in use by previous process (PID: {', '.join(map(str, killed))}) — stopped it successfully."
                self.logs.append(msg)
                print(f"ℹ️ {msg}")

            # Ensure index.html exists
            index_path = os.path.join(target_directory, "index.html")
            if not os.path.exists(index_path):
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(f"<!DOCTYPE html><html><head><title>{project_name}</title></head><body><h1>Loading {project_name}...</h1></body></html>")

            # 3. Create a dedicated runner script with strict no-cache headers
            runner_script = os.path.join(target_directory, "_sandbox_server.py")
            script_code = f"""import http.server
import socketserver
import os

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass

os.chdir(r'{target_directory}')
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', {target_port}), NoCacheHTTPRequestHandler) as httpd:
    httpd.serve_forever()
"""
            with open(runner_script, "w", encoding="utf-8") as f:
                f.write(script_code)

            # 4. Launch dedicated Subprocess
            print(f"🚀 Starting [{project_name}] on port {target_port}...")
            proc = subprocess.Popen(
                [sys.executable, runner_script],
                cwd=target_directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None
            )

            self.active_process = proc
            self.active_pid = proc.pid
            self.active_port = target_port
            self.active_project_id = project_id
            self.active_directory = target_directory

            # Verify startup
            time.sleep(0.4)
            is_up = self.is_port_in_use(target_port)
            if is_up:
                print(f"✅ [{project_name}] is LIVE on http://127.0.0.1:{target_port} (PID: {proc.pid})")
                return {
                    "status": "running",
                    "pid": proc.pid,
                    "port": target_port,
                    "url": f"http://127.0.0.1:{target_port}",
                    "directory": target_directory,
                    "project_id": project_id,
                    "message": f"Starting {project_name} on port {target_port} (PID: {proc.pid})"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to bind port {target_port} for {project_name}",
                    "pid": proc.pid,
                    "port": target_port,
                    "url": f"http://127.0.0.1:{target_port}"
                }

    def _internal_stop(self) -> Optional[int]:
        stopped_pid = None
        if self.active_process:
            try:
                pid = self.active_process.pid
                stopped_pid = pid
                print(f"🛑 Terminating tracked project server process (PID: {pid})...")
                
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    try:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    except Exception:
                        self.active_process.kill()
                else:
                    self.active_process.kill()

                self.active_process.wait(timeout=1.0)
            except Exception as e:
                print(f"⚠️ Warning stopping active process: {str(e)}")
            finally:
                self.active_process = None

        if self.active_port:
            self.kill_port_processes(self.active_port)

        self.active_pid = None
        self.active_project_id = None
        self.active_directory = None
        return stopped_pid

    def stop_project_server(self) -> Dict[str, Any]:
        """
        Explicitly stops the tracked subprocess and cleans up port 8080.
        """
        with self.lock:
            stopped_pid = self._internal_stop()
            return {
                "status": "stopped",
                "stopped_pid": stopped_pid,
                "port": self.active_port
            }

    def get_status(self) -> Dict[str, Any]:
        is_alive = False
        if self.active_process:
            is_alive = self.active_process.poll() is None

        return {
            "running": is_alive,
            "pid": self.active_pid if is_alive else None,
            "port": self.active_port,
            "project_id": self.active_project_id if is_alive else None,
            "directory": self.active_directory if is_alive else None,
            "url": f"http://127.0.0.1:{self.active_port}" if is_alive else None
        }

sandbox_manager = DedicatedProcessSandboxRunner(default_port=8080)
