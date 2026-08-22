import re
import requests

def get_api(api_base: str, endpoint: str) -> dict:
    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def hour_to_int(t_str: str) -> int:
    return int(t_str.split(":")[0])

def int_to_hour(h: int) -> str:
    return f"{h:02d}:00"

def manhattan(p1: tuple, p2: tuple) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

# --- Problem 1: Venues ---
def find_venues(api_base: str, day: str, time: str) -> str:
    data = get_api(api_base, f"/venues/{day}")
    target_h = hour_to_int(time)
    
    open_venues = []
    for venue in data.get("venues", []):
        for start, end in venue.get("available", []):
            if hour_to_int(start) <= target_h < hour_to_int(end):
                open_venues.append(venue["name"])
                break
                
    return ", ".join(open_venues)

# --- Problem 2: Meeting Time ---
def parse_inbox(inbox_text: str, target_day: str):
    accepted, tentative = set(), set()
    messages = inbox_text.split("From: ")
    
    for msg in messages:
        if not msg.strip():
            continue
        resp_m = re.search(r"Response:\s*(ACCEPTED|TENTATIVE|DECLINED)", msg)
        when_m = re.search(r"When:\s*([A-Za-z]+)\s*(\d{2}:00)-(\d{2}:00)", msg)
        
        if resp_m and when_m:
            resp = resp_m.group(1)
            day, start_str, end_str = when_m.groups()
            
            if day.lower() == target_day.lower():
                s_h, e_h = hour_to_int(start_str), hour_to_int(end_str)
                hours = set(range(s_h, e_h))
                if resp == "ACCEPTED":
                    accepted.update(hours)
                elif resp == "TENTATIVE":
                    tentative.update(hours)
                    
    return accepted, tentative

def find_meeting_time(api_base: str, day: str, start_range: str, end_range: str, duration_mins: int, friends: list, inbox_text: str) -> str:
    dur_hours = duration_mins // 60
    s_limit, e_limit = hour_to_int(start_range), hour_to_int(end_range)
    
    acc_busy, tent_busy = parse_inbox(inbox_text, day)
    hard_busy = set(acc_busy)
    
    # Fetch friends' busy hours
    for friend in friends:
        data = get_api(api_base, f"/schedule/{friend}/{day}")
        for b_start, b_end in data.get("busy", []):
            hard_busy.update(range(hour_to_int(b_start), hour_to_int(b_end)))
            
    # Pass 1: Clean window (overlaps neither ACCEPTED nor TENTATIVE)
    for h in range(s_limit, e_limit - dur_hours + 1):
        window = set(range(h, h + dur_hours))
        if not window.intersection(hard_busy) and not window.intersection(tent_busy):
            return f"{int_to_hour(h)}-{int_to_hour(h + dur_hours)}"
            
    # Pass 2: Overwrite tentative window
    for h in range(s_limit, e_limit - dur_hours + 1):
        window = set(range(h, h + dur_hours))
        if not window.intersection(hard_busy):
            return f"{int_to_hour(h)}-{int_to_hour(h + dur_hours)}"
            
    return ""

# --- Problem 3: Meeting Point ---
def find_meeting_point(api_base: str, day: str, android_x: int, android_y: int, friends: list) -> list:
    people_locs = [(android_x, android_y)]
    for friend in friends:
        loc = get_api(api_base, f"/location/{friend}/{day}")
        people_locs.append((loc["x"], loc["y"]))
        
    best_pt = None
    min_dist = float("inf")
    
    # Brute-force 10x10 grid for absolute minimum Manhattan sum
    for gx in range(10):
        for gy in range(10):
            dist = sum(manhattan((gx, gy), p) for p in people_locs)
            if dist < min_dist:
                min_dist = dist
                best_pt = [gx, gy]
                
    return best_pt

# --- Problem 4: Outing Optimization ---
def plan_outing(api_base: str, day: str, android_x: int, android_y: int, friends: list, start_range: str, end_range: str, duration_mins: int, inbox_text: str) -> str:
    # 1. Determine Window
    window = find_meeting_time(api_base, day, start_range, end_range, duration_mins, friends, inbox_text)
    if not window:
        return "No valid window"
        
    end_time_str = window.split("-")[1]
    end_h = hour_to_int(end_time_str)
    
    # 2. Get Open Venues
    venues_data = get_api(api_base, f"/venues/{day}").get("venues", [])
    valid_venues = []
    for v in venues_data:
        for v_start, v_end in v.get("available", []):
            if hour_to_int(v_start) <= end_h < hour_to_int(v_end):
                valid_venues.append(v)
                break
                
    if not valid_venues:
        return "No valid venue"
        
    # 3. Collect participant locations
    participants = [(android_x, android_y)]
    for friend in friends:
        loc = get_api(api_base, f"/location/{friend}/{day}")
        participants.append((loc["x"], loc["y"]))
        
    # 4. Global Optimization: Minimize total travel across all grid points and open venues
    best_total_cost = float("inf")
    best_pt = [0, 0]
    best_venue_name = ""
    
    for gx in range(10):
        for gy in range(10):
            meet_pt = (gx, gy)
            travel_to_meet = sum(manhattan(p, meet_pt) for p in participants)
            
            for venue in valid_venues:
                venue_pt = (venue["x"], venue["y"])
                travel_to_eat = manhattan(meet_pt, venue_pt)
                total_cost = travel_to_meet + travel_to_eat
                
                if total_cost < best_total_cost:
                    best_total_cost = total_cost
                    best_pt = [gx, gy]
                    best_venue_name = venue["name"]
                    
    return f"Meeting Window: {window}, Meeting Point: {best_pt}, Place to Eat: {best_venue_name}"
