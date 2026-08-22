import json
from fastapi import FastAPI, Request
from mcp.server.fastmcp import FastMCP
import logic

# Initialize FastMCP instance
mcp = FastMCP("ghost_chains_stage3")

@mcp.tool()
def find_venues(api_base: str, day: str, time: str) -> str:
    """Finds open food/drink venues on a given day and hour."""
    return logic.find_venues(api_base, day, time)

@mcp.tool()
def find_meeting_time(api_base: str, day: str, start_range: str, end_range: str, duration_mins: int, friends: list[str], inbox_text: str) -> str:
    """Finds the optimal meeting time window considering busy schedules and inbox responses."""
    return logic.find_meeting_time(api_base, day, start_range, end_range, duration_mins, friends, inbox_text)

@mcp.tool()
def find_meeting_point(api_base: str, day: str, android_x: int, android_y: int, friends: list[str]) -> str:
    """Finds optimal meeting coordinates [x, y] minimizing total travel distance."""
    pt = logic.find_meeting_point(api_base, day, android_x, android_y, friends)
    return json.dumps(pt)

@mcp.tool()
def plan_outing(api_base: str, day: str, android_x: int, android_y: int, friends: list[str], start_range: str, end_range: str, duration_mins: int, inbox_text: str) -> str:
    """Orchestrates full outing: selects window, optimal meeting point, and restaurant."""
    return logic.plan_outing(api_base, day, android_x, android_y, friends, start_range, end_range, duration_mins, inbox_text)

# Create standard FastAPI app and mount FastMCP's SSE app
app = FastAPI(title="Stage 3 MCP Server")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Mount the inner SSE sub-application to root
mcp_sse_app = mcp.sse_app()
app.mount("/", mcp_sse_app)
