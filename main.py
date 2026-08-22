import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
import httpx

# ---------- MCP imports ----------
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    GetPromptResult,
    Prompt,
    PromptMessage,
    ListToolsResult,
)
from mcp.server.sse import SseServerTransport

# ---------- FastAPI app ----------
app = FastAPI(title="Ghost Chains + MCP Server")

# ---------- MCP Server instance ----------
mcp_server = Server("ghost-chains-mcp")

# ---------- Tool definitions ----------
@mcp_server.list_tools()
async def list_tools() -> ListToolsResult:
    return ListToolsResult(
        tools=[
            Tool(
                name="get_venues",
                description="Get the list of venues open on a given weekday (Monday..Sunday). Returns name, coordinates, and available time slots.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "day": {"type": "string", "enum": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]}
                    },
                    "required": ["day"]
                }
            ),
            Tool(
                name="get_schedule",
                description="Get the busy intervals for a person on a given day.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string"},
                        "day": {"type": "string", "enum": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]}
                    },
                    "required": ["person","day"]
                }
            ),
            Tool(
                name="get_location",
                description="Get the grid coordinates [x, y] of a person on a given day.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string"},
                        "day": {"type": "string", "enum": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]}
                    },
                    "required": ["person","day"]
                }
            ),
        ]
    )

# ---------- Tool implementations ----------
async def call_remote_api(endpoint: str, params: dict) -> dict:
    """Helper to call the external API (mock or real)."""
    # In a real scenario, you would call the actual endpoints provided.
    # For demo, we return mock data. Replace with real HTTP calls.
    # Example: return await httpx.get(f"https://api.example.com/{endpoint}", params=params).json()
    # For now, we simulate:
    if endpoint == "venues":
        return {
            "day": params["day"],
            "venues": [
                {"name": "Amber Hall", "x": 6, "y": 3, "available": [["16:00", "21:00"]]},
                {"name": "Nine Quarters", "x": 7, "y": 3, "available": [["11:00", "16:00"]]}
            ]
        }
    elif endpoint == "schedule":
        # Mock schedule
        return {"person": params["person"], "day": params["day"], "busy": [["08:00", "11:00"], ["16:00", "17:00"]]}
    elif endpoint == "location":
        return {"person": params["person"], "day": params["day"], "x": 0, "y": 6}
    else:
        return {}

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        if name == "get_venues":
            day = arguments["day"]
            data = await call_remote_api("venues", {"day": day})
            result_text = json.dumps(data, indent=2)
        elif name == "get_schedule":
            person = arguments["person"]
            day = arguments["day"]
            data = await call_remote_api("schedule", {"person": person, "day": day})
            result_text = json.dumps(data, indent=2)
        elif name == "get_location":
            person = arguments["person"]
            day = arguments["day"]
            data = await call_remote_api("location", {"person": person, "day": day})
            result_text = json.dumps(data, indent=2)
        else:
            return CallToolResult(content=[TextContent(type="text", text=f"Unknown tool: {name}")], isError=True)

        return CallToolResult(content=[TextContent(type="text", text=result_text)])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")], isError=True)

# ---------- SSE transport ----------
transport = SseServerTransport("/mcp/sse")

@mcp_server.router.get("/mcp/sse")
async def handle_sse(request: Request):
    async with transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

@mcp_server.router.post("/mcp/messages")
async def handle_messages(request: Request):
    # Handle incoming messages from the client
    # This is a simplified version; you might need to extract session ID
    # from headers or query params.
    # The SSE transport already manages this; we just forward to the server.
    # For full implementation, see the mcp SDK examples.
    return JSONResponse({"status": "ok"})

# ---------- Include MCP router in FastAPI ----------
app.include_router(mcp_server.router)

# ---------- Ghost Chains endpoints (Phase 1-3) ----------
# (Include your existing ghost-chains code here, or keep separate)
# For brevity, I'll include the minimal required endpoints.

@app.get("/ghost-chains/health")
async def health():
    return {"status": "ok"}

@app.post("/ghost-chains/reset")
async def reset():
    # Reset your graph state
    return {"clearTransactions": True}

@app.post("/ghost-chains/transactions")
async def transactions(req: dict):
    # Your transaction scoring logic
    # For demo, return riskScore 0.0
    return {"transactions": [{"txId": t["txId"], "riskScore": 0.0} for t in req.get("transactions", [])]}

# ---------- Main ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
