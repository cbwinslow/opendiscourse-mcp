#!/bin/bash
# Universal AI Gateway Setup Script
# Implements centralized AI agent management and control

set -e

GATEWAY_DIR="$HOME/ai-gateway"
KNOWLEDGE_BASE="$HOME/Knowledge-Base"
RULES_PATH="$KNOWLEDGE_BASE/ai_agents/rules/universal_operational_rules.md"

echo "🚀 Setting up Universal AI Gateway..."

# Create gateway directory structure
echo "📁 Creating gateway directory structure..."
mkdir -p "$GATEWAY_DIR"/{core,rules,tools,api,monitoring,config,tests}

# Create main gateway server
echo "🔧 Creating gateway server..."
cat > "$GATEWAY_DIR/gateway.py" << 'EOF'
#!/usr/bin/env python3
"""
Universal AI Gateway Server
Centralized management and control for all AI agents
"""

import json
import logging
import asyncio
import websockets
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Agent:
    id: str
    name: str
    type: str
    version: str
    capabilities: List[str]
    registered_at: datetime
    last_seen: datetime
    status: str = "active"

@dataclass
class Operation:
    id: str
    agent_id: str
    type: str
    target: str
    action: str
    parameters: Dict[str, Any]
    timestamp: datetime
    status: str = "pending"

class RuleEngine:
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.universal_rules = self.load_rules()
        self.violations = []
    
    def load_rules(self) -> Dict[str, Any]:
        """Load universal operational rules"""
        if not self.rules_path.exists():
            logger.error(f"Rules file not found: {self.rules_path}")
            return {}
        
        # For now, return basic rule structure
        # TODO: Parse markdown rules file
        return {
            "ssh_protection": {
                "forbidden": ["ssh", "scp", "sftp"],
                "protected_files": ["~/.ssh/", "/etc/ssh/"]
            },
            "system_protection": {
                "forbidden_dirs": ["/etc/", "/usr/local/", "/boot/"],
                "protected_commands": ["rm", "chmod", "chown"]
            },
            "security": {
                "forbidden_patterns": ["password", "secret", "token", "key"]
            }
        }
    
    def validate_operation(self, operation: Operation) -> tuple[bool, str]:
        """Validate operation against universal rules"""
        # SSH protection check
        if operation.type in ["ssh", "scp", "sftp"]:
            return False, "SSH operations are forbidden by universal rules"
        
        # System protection check
        if operation.target.startswith("/etc/") or operation.target.startswith("/usr/local/"):
            return False, "System file modifications are forbidden by universal rules"
        
        # Security check
        for param in operation.parameters.values():
            if isinstance(param, str) and any(pattern in param.lower() for pattern in ["password", "secret", "token", "key"]):
                return False, "Potential credential exposure detected"
        
        return True, "Operation validated"

class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.connections: Dict[str, WebSocket] = {}
    
    def register_agent(self, agent_info: Dict[str, Any]) -> Agent:
        """Register new AI agent"""
        agent = Agent(
            id=agent_info["id"],
            name=agent_info["name"],
            type=agent_info["type"],
            version=agent_info["version"],
            capabilities=agent_info.get("capabilities", []),
            registered_at=datetime.now(),
            last_seen=datetime.now()
        )
        
        self.agents[agent.id] = agent
        logger.info(f"Agent registered: {agent.name} ({agent.id})")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def update_last_seen(self, agent_id: str):
        """Update agent last seen timestamp"""
        if agent_id in self.agents:
            self.agents[agent_id].last_seen = datetime.now()

class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.permissions = {}
    
    def register_tool(self, tool_info: Dict[str, Any]):
        """Register new tool"""
        self.tools[tool_info["name"]] = tool_info
        logger.info(f"Tool registered: {tool_info['name']}")
    
    def check_permission(self, agent_id: str, tool_name: str) -> bool:
        """Check if agent can use tool"""
        # For now, allow all tools to all agents
        # TODO: Implement proper permission system
        return tool_name in self.tools

class AIGateway:
    def __init__(self, rules_path: Path):
        self.app = FastAPI(title="Universal AI Gateway", version="1.0.0")
        self.rule_engine = RuleEngine(rules_path)
        self.agent_manager = AgentManager()
        self.tool_registry = ToolRegistry()
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.setup_routes()
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.post("/api/v1/agents/register")
        async def register_agent(agent_info: Dict[str, Any]):
            try:
                agent = self.agent_manager.register_agent(agent_info)
                return {"status": "success", "agent": asdict(agent)}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/agents/{agent_id}")
        async def get_agent(agent_id: str):
            agent = self.agent_manager.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            return asdict(agent)
        
        @self.app.post("/api/v1/operations/validate")
        async def validate_operation(operation: Dict[str, Any]):
            try:
                op = Operation(
                    id=operation["id"],
                    agent_id=operation["agent_id"],
                    type=operation["type"],
                    target=operation["target"],
                    action=operation["action"],
                    parameters=operation.get("parameters", {}),
                    timestamp=datetime.now()
                )
                
                is_valid, message = self.rule_engine.validate_operation(op)
                return {"valid": is_valid, "message": message}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/rules")
        async def get_rules():
            return self.rule_engine.universal_rules
        
        @self.app.get("/api/v1/compliance")
        async def get_compliance():
            return {
                "total_agents": len(self.agent_manager.agents),
                "active_agents": len([a for a in self.agent_manager.agents.values() if a.status == "active"]),
                "violations": len(self.rule_engine.violations),
                "rules_loaded": len(self.rule_engine.universal_rules)
            }
        
        @self.app.websocket("/ws/agent/{agent_id}")
        async def websocket_endpoint(websocket: WebSocket, agent_id: str):
            await websocket.accept()
            self.agent_manager.connections[agent_id] = websocket
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle different message types
                    if message["type"] == "heartbeat":
                        self.agent_manager.update_last_seen(agent_id)
                        await websocket.send_text(json.dumps({"type": "heartbeat_ack"}))
                    
                    elif message["type"] == "operation":
                        # Validate operation
                        operation_data = message["operation"]
                        is_valid, validation_message = self.rule_engine.validate_operation(
                            Operation(**operation_data)
                        )
                        
                        response = {
                            "type": "operation_response",
                            "operation_id": operation_data["id"],
                            "valid": is_valid,
                            "message": validation_message
                        }
                        
                        await websocket.send_text(json.dumps(response))
                        
            except WebSocketDisconnect:
                if agent_id in self.agent_manager.connections:
                    del self.agent_manager.connections[agent_id]
                logger.info(f"Agent disconnected: {agent_id}")

def main():
    """Main gateway server"""
    import os
    import uvicorn
    
    # Configuration
    rules_path = Path(os.getenv("RULES_PATH", "~/Knowledge-Base/ai_agents/rules/universal_operational_rules.md")).expanduser()
    
    # Create gateway
    gateway = AIGateway(rules_path)
    
    # Start server
    uvicorn.run(gateway.app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
EOF

# Create requirements file
echo "📦 Creating requirements file..."
cat > "$GATEWAY_DIR/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.0
PyYAML==6.0.1
python-multipart==0.0.6
EOF

# Create configuration
echo "⚙️ Creating configuration..."
cat > "$GATEWAY_DIR/config/gateway.yaml" << 'EOF'
# Universal AI Gateway Configuration

server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

rules:
  path: "~/Knowledge-Base/ai_agents/rules/universal_operational_rules.md"
  auto_reload: true
  validation_mode: "strict"

agents:
  registration_required: true
  session_timeout: 3600  # 1 hour
  max_concurrent_operations: 10

tools:
  registry_enabled: true
  permission_required: false  # TODO: Set to true when permissions implemented
  usage_tracking: true

monitoring:
  metrics_enabled: true
  logging_level: "INFO"
  audit_trail: true

security:
  authentication_required: false  # TODO: Set to true when auth implemented
  tls_enabled: false
  api_key_required: false
EOF

# Create agent client library
echo "🔌 Creating agent client library..."
cat > "$GATEWAY_DIR/client.py" << 'EOF'
#!/usr/bin/env python3
"""
Universal AI Gateway Client
For AI agents to connect to the gateway
"""

import json
import asyncio
import websockets
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests

@dataclass
class AgentInfo:
    id: str
    name: str
    type: str
    version: str
    capabilities: list = None

class AIGatewayClient:
    def __init__(self, gateway_url: str = "ws://localhost:8080"):
        self.gateway_url = gateway_url
        self.http_url = gateway_url.replace("ws://", "http://").replace("wss://", "https://")
        self.websocket = None
        self.agent_info = None
    
    async def register(self, agent_info: AgentInfo):
        """Register agent with gateway"""
        self.agent_info = agent_info
        
        # Register via HTTP API
        response = requests.post(
            f"{self.http_url}/api/v1/agents/register",
            json={
                "id": agent_info.id,
                "name": agent_info.name,
                "type": agent_info.type,
                "version": agent_info.version,
                "capabilities": agent_info.capabilities or []
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Agent registered: {agent_info.name}")
            return True
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
    
    async def connect(self):
        """Connect to gateway via WebSocket"""
        try:
            self.websocket = await websockets.connect(
                f"{self.gateway_url}/ws/agent/{self.agent_info.id}"
            )
            print(f"✅ Connected to gateway as {self.agent_info.name}")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def _message_handler(self):
        """Handle incoming messages from gateway"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data["type"] == "heartbeat_ack":
                    # Heartbeat acknowledged
                    pass
                
                elif data["type"] == "operation_response":
                    # Operation validation response
                    print(f"Operation {data['operation_id']}: {data['message']}")
                
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Disconnected from gateway")
    
    async def validate_operation(self, operation: Dict[str, Any]) -> tuple[bool, str]:
        """Validate operation with gateway"""
        if not self.websocket:
            return False, "Not connected to gateway"
        
        # Send operation for validation
        message = {
            "type": "operation",
            "operation": operation
        }
        
        await self.websocket.send(json.dumps(message))
        
        # Wait for response (simplified - in real implementation, use futures)
        await asyncio.sleep(0.1)
        
        # For now, return True (real implementation would wait for actual response)
        return True, "Validation requested"
    
    async def heartbeat(self):
        """Send heartbeat to gateway"""
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "heartbeat"}))

# Example usage
async def example_agent():
    """Example of how an AI agent would use the gateway"""
    
    # Create agent info
    agent_info = AgentInfo(
        id="example_agent_001",
        name="Code Assistant",
        type="coding",
        version="1.0.0",
        capabilities=["code_generation", "file_editing"]
    )
    
    # Create client
    client = AIGatewayClient()
    
    # Register and connect
    if await client.register(agent_info):
        if await client.connect():
            
            # Example operation validation
            operation = {
                "id": "op_001",
                "agent_id": agent_info.id,
                "type": "file_edit",
                "target": "/home/user/test.py",
                "action": "modify",
                "parameters": {"content": "print('hello')"}
            }
            
            is_valid, message = await client.validate_operation(operation)
            print(f"Operation valid: {is_valid}, Message: {message}")

if __name__ == "__main__":
    asyncio.run(example_agent())
EOF

# Create startup script
echo "🚀 Creating startup script..."
cat > "$GATEWAY_DIR/start_gateway.sh" << 'EOF'
#!/bin/bash
# Start the Universal AI Gateway

set -e

GATEWAY_DIR="$(dirname "$0")"
cd "$GATEWAY_DIR"

echo "🚀 Starting Universal AI Gateway..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set environment variables
export RULES_PATH="$HOME/Knowledge-Base/ai_agents/rules/universal_operational_rules.md"

# Start gateway server
echo "🌐 Starting gateway server on http://localhost:8080"
python gateway.py
EOF

# Make scripts executable
chmod +x "$GATEWAY_DIR/start_gateway.sh"
chmod +x "$GATEWAY_DIR/client.py"

# Create systemd service
echo "🔧 Creating systemd service..."
cat > "$HOME/.config/systemd/user/ai-gateway.service" << EOF
[Unit]
Description=Universal AI Gateway
After=network.target

[Service]
Type=simple
User=cbwinslow
WorkingDirectory=$GATEWAY_DIR
Environment=RULES_PATH=$KNOWLEDGE_BASE/ai_agents/rules/universal_operational_rules.md
ExecStart=$GATEWAY_DIR/start_gateway.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

echo "✅ Universal AI Gateway setup complete!"
echo ""
echo "📁 Gateway installed at: $GATEWAY_DIR"
echo "🚀 To start: $GATEWAY_DIR/start_gateway.sh"
echo "🔧 Or enable as service: systemctl --user enable ai-gateway"
echo ""
echo "📖 Documentation: $KNOWLEDGE_BASE/ai_agents/UNIVERSAL_AI_GATEWAY_ARCHITECTURE.md"
echo "📋 Universal Rules: $RULES_PATH"
echo ""
echo "🌐 Gateway API will be available at: http://localhost:8080"
echo "📊 Compliance dashboard: http://localhost:8080/api/v1/compliance"
echo "📋 Current rules: http://localhost:8080/api/v1/rules"