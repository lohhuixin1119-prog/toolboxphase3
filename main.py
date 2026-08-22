import json
from fastapi import FastAPI, Request
from starlette.routing import Mount
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import (
    ListToolsResult,
    CallToolResult,
    PaginatedRequestParams,
    Tool,
    TextContent
)

import logic

# 1. Define Tool Definitions
TOOLS = [
    Tool(
        name="find_venues",
        description="Finds open food/drink venues on a given day and hour.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base": {"type": "string"},
                "day": {"type": "string"},
                "time": {"type": "string"}
            },
            "required": ["api_base", "day", "time"]
        }
    ),
    Tool(
        name="find_meeting_time",
        description="Finds the optimal meeting time window considering busy schedules and inbox responses.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base": {"type": "string"},
                "day": {"type": "string"},
                "start_range": {"type": "string"},
                "end_range": {"type": "string"},
                "duration_mins": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}},
                "inbox_text": {"type": "string"}
            },
            "required": ["api_base", "day", "start_range", "end_range", "duration_mins", "friends", "inbox_text"]
        }
    ),
    Tool(
        name="find_meeting_point",
        description="Finds optimal meeting coordinates [x, y] minimizing total travel distance.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base": {"type": "string"},
                "day": {"type": "string"},
                "android_x": {"type": "integer"},
                "android_y": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["api_base", "day", "android_x", "android_y", "friends"]
        }
    ),
    Tool(
        name="plan_outing",
        description="Orchestrates full outing: selects window, optimal meeting point, and restaurant.",
        inputSchema={
            "type": "object",
            "properties": {
                "api_base": {"type": "string"},
                "day": {"type": "string"},
                "android_x": {"type": "integer"},
                "android_y": {"type": "integer"},
                "friends": {"type": "array", "items": {"type": "string"}},
                "start_range": {"type": "string"},
                "end_range": {"type": "string"},
                "duration_mins": {"type": "integer"},
                "inbox_text": {"type": "string"}
            },
            "required": ["api_base", "day", "android_x", "android_y", "friends", "start_range", "end_range", "duration_mins", "inbox_text"]
        }
    )
]

# 2. Handlers
async def handle_list_tools(params: PaginatedRequestParams | None = None) -> ListToolsResult:
    return ListToolsResult(tools=TOOLS)

async def handle_call_tool(name: str, arguments: dict | None = None) -> CallToolResult:
    args = arguments or {}
    result = ""
    
    if name == "find_venues":
        result = logic.find_venues(args["api_base"], args["day"], args["time"])
    elif name == "find_meeting_time":
        result = logic.find_meeting_time(
            args["api_base"], args["day"], args["start_range"], 
            args["end_range"], args["duration_mins"], args["friends"], args["inbox_text"]
        )
    elif name == "find_meeting_point":
        pt = logic.find_meeting_point(
            args["api_base"], args["day"], args["android_x"], 
            args["android_y"], args["friends"]
        )
        result = json.dumps(pt)
    elif name == "plan_outing":
        result = logic.plan_outing(
            args["api_base"], args["day"], args["android_x"], 
            args["android_y"], args["friends"], args["start_range"], 
            args["end_range"], args["duration_mins"], args["inbox_text"]
        )
    else:
        raise ValueError(f"Unknown tool: {name}")

    return CallToolResult(content=[TextContent(type="text", text=str(result))])

# 3. Server Setup
mcp_server = Server("ghost_chains_stage3")
mcp_server.list_tools()(handle_list_tools)
mcp_server.call_tool()(handle_call_tool)

app = FastAPI(title="Stage 3 MCP Server")

# Initialize SSE Transport relative to /messages/
sse = SseServerTransport("/messages/")

# Directly append the POST message handler to avoid sub-app route dropping
app.router.routes.append(Mount("/messages", app=sse.handle_post_message))

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )
