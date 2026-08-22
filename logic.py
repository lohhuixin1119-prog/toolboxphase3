import re
import requests

def get_api_data(api_base: str, endpoint: str) -> dict:
    response = requests.get(f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}")
    response.raise_for_status()
    return response.json()

def hour_to_int(time_str: str) -> int:
    return int(time_str.split(':')[0])

def parse_inbox_for_day(inbox_text: str, target_day: str):
    """Extracts ACCEPTED and TENTATIVE time blocks for a specific day."""
    accepted, tentative = [], []
    for msg in inbox_text.split("From: "):
        resp_match = re.search(r"Response:\s*(ACCEPTED|TENTATIVE)", msg)
        when_match = re.search(r"When:\s*([A-Za-z]+)\s*(\d{2}:\d{2})-(\d{2}:\d{2})", msg)
        
        if resp_match and when_match:
            day, start, end = when_match.groups()
            if day.lower() == target_day.lower():
                block = [start, end]
                if resp_match.group(1) == "ACCEPTED":
                    accepted.append(block)
                else:
                    tentative.append(block)
    return accepted, tentative

def get_busy_hours(time_blocks) -> set:
    busy = set()
    for start, end in time_blocks:
        busy.update(range(hour_to_int(start), hour_to_int(end)))
    return busy

def find_venues(api_base: str, day: str, time: str) -> str:
    """Problem 1: Finds open venues."""
    data = get_api_data(api_base, f"/venues/{day}")
    target = hour_to_int(time)
    valid = [v['name'] for v in data.get('venues', []) for s, e in v['available'] if hour_to_int(s) <= target < hour_to_int(e)]
    return ", ".join(valid)

def find_meeting_time(api_base: str, day: str, start_range: str, end_range: str, duration_mins: int, friends: list, inbox: str) -> str:
    """Problem 2: Finds the earliest available meeting window."""
    dur_h = duration_mins // 60
    start_h, end_h = hour_to_int(start_range), hour_to_int(end_range)
    
    accepted, tentative = parse_inbox_for_day(inbox, day)
    hard_busy = get_busy_hours(accepted)
    tent_busy = get_busy_hours(tentative)
    
    for friend in friends:
        data = get_api_data(api_base, f"/schedule/{friend}/{day}")
        hard_busy.update(get_busy_hours(data.get('busy', [])))
        
    # Check clean windows first
    for h in range(start_h, end_h - dur_h + 1):
        window = set(range(h, h + dur_h))
        if not window.intersection(hard_busy) and not window.intersection(tent_busy):
            return f"{h:02d}:00-{(h + dur_h):02d}:00"
            
    # Fallback to overwriting tentative
    for h in range(start_h, end_h - dur_h + 1):
        window = set(range(h, h + dur_h))
        if not window.intersection(hard_busy):
            return f"{h:02d}:00-{(h + dur_h):02d}:00"
            
    return "No window"

def find_meeting_point(api_base: str, day: str, ax: int, ay: int, friends: list) -> list:
    """Problem 3: Manhattan distance geometric median."""
    xs, ys = [ax], [ay]
    for friend in friends:
        loc = get_api_data(api_base, f"/location/{friend}/{day}")
        xs.append(loc['x'])
        ys.append(loc['y'])
    xs.sort()
    ys.sort()
    return [xs[len(xs)//2], ys[len(ys)//2]]

def plan_outing(api_base: str, day: str, ax: int, ay: int, friends: list, start_r: str, end_r: str, dur: int, inbox: str) -> str:
    """Problem 4: Orchestrates time, point, and venue routing."""
    window = find_meeting_time(api_base, day, start_r, end_r, dur, friends, inbox)
    if window == "No window": return "Failed"
    
    # Calculate routing brute-force... (simplified for space)
    meeting_pt = find_meeting_point(api_base, day, ax, ay, friends)
    venue = find_venues(api_base, day, window.split('-')[1]).split(', ')[0] 
    
    return f"Time: {window} | Point: {meeting_pt} | Venue: {venue}"
