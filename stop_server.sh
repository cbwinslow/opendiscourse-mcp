#!/bin/bash
# Stop the MCP FastAPI server

if [ -f ".server_pid" ]; then
    SERVER_PID=$(cat .server_pid)
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "🛑 Stopping MCP Server (PID: $SERVER_PID)..."
        kill $SERVER_PID
        rm .server_pid
        echo "✅ MCP Server stopped"
    else
        echo "⚠️  Server process not found"
        rm .server_pid
    fi
else
    echo "⚠️  No server PID file found"
    # Try to find and kill any uvicorn processes
    UVICORN_PIDS=$(pgrep -f "uvicorn.*mcp_server")
    if [ -n "$UVICORN_PIDS" ]; then
        echo "🛑 Killing uvicorn processes: $UVICORN_PIDS"
        kill $UVICORN_PIDS
    fi
fi
