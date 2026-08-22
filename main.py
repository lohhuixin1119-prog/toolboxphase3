import json
from fastapi import FastAPI
from starlette.requests import Request
from mcp.server import Server, ServerRequestContext
from mcp.server.sse import SseServerTransport
from mcp.types import (
    ListToolsResult,
    CallToolResult,
    PaginatedRequestParams,
    Tool,
    TextContent
)

import logic

# 1. Define Tool Schemas
TOOLS = [
    Tool(
        name="find_venues",
        description="Finds venues open at a specific time.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base_url": {"type": "string"},
                "day": {"type": "string"},
                "time": {"type": "string"}
            },
            "required": ["api_base_url", "day", "time"]
        }
    ),
    Tool(
        name="find_meeting_time",
        description="Finds the best available meeting window.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base_url": {"type": "string"},
                "day": {"type": "string"},
                "start_range": {"type": "string"},
                "end_range": {"type": "string"},
                "duration_mins": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}},
                "inbox_text": {"type": "string"}
            },
            "required": ["api_base_url", "day", "start_range", "end_range", "duration_mins", "friends", "inbox_text"]
        }
    ),
    Tool(
        name="find_meeting_point",
        description="Finds optimal meeting coordinates [x, y].",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base_url": {"type": "string"},
                "day": {"type": "string"},
                "android_x": {"type": "integer"},
                "android_y": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["api_base_url", "day", "android_x", "android_y", "friends"]
        }
    ),
    Tool(
        name="plan_outing",
        description="Orchestrates complete outing plan.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base_url": {"type": "string"},
                "day": {"type": "string"},
                "android_x": {"type": "integer"},
                "android_y": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}},
                "start_range": {"type": "string"},
                "end_range": {"type": "string"},
                "duration_mins": {"type": "integer"},
                "inbox_text": {"type": "string"}
            },
            "required": ["api_base_url", "day", "android_x", "android_y", "friends", "start_range", "end_range", "duration_mins", "inbox_text"]
        }
    )
]

# 2. Handlers for mcp 2.0.0
async def handle_list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)

async def handle_call_tool(ctx: ServerRequestContext, name: str, arguments: dict | None) -> CallToolResult:
    args = arguments or {}
    result = ""
    
    if name == "find_venues":
        result = logic.find_venues(args["api_base_url"], args["day"], args["time"])
    elif name == "find_meeting_time":
        result = logic.find_meeting_time(
            args["api_base_url"], args["day"], args["start_range"], 
            args["end_range"], args["duration_mins"], args["friends"], args["inbox_text"]
        )
    elif name == "find_meeting_point":
        res = logic.find_meeting_point(
            args["api_base_url"], args["day"], args["android_x"], 
            args["android_y"], args["friends"]
        )
        result = json.dumps(res)
    elif name == "plan_outing":
        result = logic.plan_outing(
            args["api_base_url"], args["day"], args["android_x"], 
            args["android_y"], args["friends"], args["start_range"], 
            args["end_range"], args["duration_mins"], args["inbox_text"]
        )
    else:
        raise ValueError(f"Unknown tool: {name}")

    return CallToolResult(content=[TextContent(type="text", text=str(result))])

# 3. Instantiate MCP Server with handlers
mcp_server = Server(
    "ghost_chains_stage3",
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool
)

# 4. Instantiate FastAPI app (Must be named 'app' for uvicorn main:app)
app = FastAPI(title="Ghost Chains MCP Server")
sse = SseServerTransport("/messages")

@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "MCP Server Running"}

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)
