import os
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# 1. Initialize stable MCP Server
mcp = Server("ghost_chains_stage3")

# 2. Define tools explicitly
@mcp.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="example_tool",
            description="An example tool that echoes text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"}
                },
                "required": ["text"]
            }
        )
    ]

@mcp.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "example_tool":
        return [TextContent(type="text", text=f"Echo: {arguments.get('text')}")]
    raise ValueError(f"Unknown tool: {name}")

# 3. Mount to FastAPI
app = FastAPI(title="Ghost Chains")
sse = SseServerTransport("/messages")

@app.get("/")
async def health_check():
    # Required to pass Render's 15-second port binding timeout
    return {"status": "ok", "message": "Ghost Chains is running"}

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run(streams[0], streams[1], mcp.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)
