#!/bin/bash
set -e

echo "=================================================================="
echo " Starting Multi-Agent Collaborative System Microservice..."
echo "=================================================================="

# Ensure requirements are installed
python3 -m pip install -q --user -r requirements.txt || true

# Start backend service
python3 start.py
