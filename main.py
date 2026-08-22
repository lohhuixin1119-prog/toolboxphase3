from fastapi import FastAPI
import uvicorn
from mcp.server.fastmcp import FastMCP
from logic import (
    get_api_data, hour_to_int, int_to_hour, get_busy_hours, 
    parse_inbox_for_day, get_optimal_meeting_point, get_best_outing_route
)

# 1. Initialize FastAPI and FastMCP
app = FastAPI(title="Stage 3 MCP Server")
mcp = FastMCP("ghost_chains_stage3")

# --- DEFINE MCP TOOLS ---

@mcp.tool()
def solve_problem_1_venues(api_base_url: str, day: str, time: str) -> str:
    """
    Finds venues open at a specific time.
    api_base_url: The base URL for the challenge APIs (e.g. 'http://localhost:8080')
    """
    data = get_api_data(api_base_url, f"/venues/{day}")
    target_hour = hour_to_int(time)
    
    valid_venues = []
    for venue in data.get('venues', []):
        for start, end in venue['available']:
            if hour_to_int(start) <= target_hour < hour_to_int(end):
                valid_venues.append(venue['name'])
                break
                
    return ", ".join(valid_venues)

@mcp.tool()
def solve_problem_2_meeting_time(api_base_url: str, day: str, start_range: str, end_range: str, duration_mins: int, friends: list[str], inbox_text: str) -> str:
    """
    Finds the best available meeting window for all friends and the android.
    """
    duration_hours = duration_mins // 60
    range_start = hour_to_int(start_range)
    range_end = hour_to_int(end_range)
    
    hard_busy_hours = set()
    tentative_hours = set()
    
    # Process Android Inbox
    accepted, tentative = parse_inbox_for_day(inbox_text, day)
    hard_busy_hours.update(get_busy_hours(accepted))
    tentative_hours.update(get_busy_hours(tentative))
    
    # Process Friends
    for friend in friends:
        data = get_api_data(api_base_url, f"/schedule/{friend}/{day}")
        hard_busy_hours.update(get_busy_hours(data.get('busy', [])))
        
    # Earliest entirely clean window
    for h in range(range_start, range_end - duration_hours + 1):
        window = set(range(h, h + duration_hours))
        if not window.intersection(hard_busy_hours) and not window.intersection(tentative_hours):
            return f"{int_to_hour(h)}-{int_to_hour(h + duration_hours)}"
            
    # Earliest window overriding tentative events
    for h in range(range_start, range_end - duration_hours + 1):
        window = set(range(h, h + duration_hours))
        if not window.intersection(hard_busy_hours):
            return f"{int_to_hour(h)}-{int_to_hour(h + duration_hours)}"
            
    return "No available window"

@mcp.tool()
def solve_problem_3_meeting_point(api_base_url: str, day: str, android_x: int, android_y: int, friends: list[str]) -> list[int]:
    """
    Finds the point on the grid [x, y] that minimizes travel for everyone.
    """
    positions = [[android_x, android_y]]
    for friend in friends:
        loc = get_api_data(api_base_url, f"/location/{friend}/{day}")
        positions.append([loc['x'], loc['y']])
        
    return get_optimal_meeting_point(positions)

@mcp.tool()
def solve_problem_4_outing(api_base_url: str, day: str, android_x: int, android_y: int, friends: list[str], start_range: str, end_range: str, duration_mins: int, inbox_text: str) -> str:
    """
    Orchestrates the entire outing (time, meeting point, and venue) to minimize total travel.
    Returns a formatted string with the window, [x, y], and venue name.
    """
    # 1. Get Time
    meeting_window = solve_problem_2_meeting_time(api_base_url, day, start_range, end_range, duration_mins, friends, inbox_text)
    if meeting_window == "No available window":
        return "Failed: No meeting time found"
        
    eating_start_time = meeting_window.split('-')[1]
    eating_hour = hour_to_int(eating_start_time)
    
    # 2. Get Open Venues for the post-meeting hour
    venues_data = get_api_data(api_base_url, f"/venues/{day}")
    valid_venues = []
    for v in venues_data.get('venues', []):
        for start, end in v['available']:
            if hour_to_int(start) <= eating_hour < hour_to_int(end):
                valid_venues.append(v)
                break
                
    # 3. Get Locations
    positions = []
    for friend in friends:
        loc = get_api_data(api_base_url, f"/location/{friend}/{day}")
        positions.append([loc['x'], loc['y']])
        
    # 4. Math Route Calculation
    meeting_pt, venue_name = get_best_outing_route(positions, [android_x, android_y], valid_venues)
    
    return f"Meeting Window: {meeting_window}\nMeeting Point: {meeting_pt}\nVenue: {venue_name}"


# --- MOUNT MCP TO FASTAPI ---

# The evaluator expects to find MCP at {teamUrl}/mcp
# FastMCP automatically creates an SSE endpoint. We can expose it via the Starlette app.
mcp_app = mcp.get_starlette_app()
app.mount("/mcp", mcp_app)

@app.get("/")
@app.head("/")
async def root():
    return {"status": "Stage 3 MCP Server Online"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
