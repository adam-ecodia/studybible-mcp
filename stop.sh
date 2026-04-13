#!/bin/bash

# Check if PID file exists
if [ ! -f server.pid ]; then
    echo "PID file not found. Server may not be running."
    exit 1
fi

# Read the PID from file
PID=$(cat server.pid)

# Kill the process
kill $PID

# Remove the PID file
rm server.pid

echo "Server with PID $PID has been stopped"