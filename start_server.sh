#!/bin/bash
# Start the MCP FastAPI server

echo "🚀 Starting MCP Server..."

# Load environment
export $(cat mcp_server/.env | xargs)

# Start server in background
.venv/bin/python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

echo "✅ MCP Server started with PID: $SERVER_PID"
echo "🌐 API available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""
echo "To stop the server: kill $SERVER_PID"

# Save PID for later
echo $SERVER_PID > .server_pid
