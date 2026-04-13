#!/bin/bash

# Load Python virtual environment and start the server in background
source venv/bin/activate
python3 -m study_bible_mcp.server --transport stdio &

# Save the PID to a file
echo $! > server.pid

echo "Server started with PID $(cat server.pid)"