#!/usr/bin/env python3
"""
Multi-Agent Collaborative System - Microservice Launcher
"""

import os
import sys
import uvicorn

def main():
    print("=" * 70)
    print(" 🚀 MULTI-AGENT COLLABORATIVE SYSTEM (AgentTeams Microservice)")
    print("=" * 70)
    print(" • Orchestrator : Manager Agent + 4 Parallel Worker Agents")
    print(" • Features     : Meeting Room SSE, Subtasks Board, Universal Model Broker")
    print(" • Dashboard UI : http://localhost:8000")
    print(" • API Docs     : http://localhost:8000/docs")
    print("=" * 70)
    print("\n👉 Starting server on http://127.0.0.1:8000 ...\n")
    
    # Run uvicorn server
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
