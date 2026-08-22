import re
import requests
from typing import List, Dict, Tuple

def get_api_data(api_base: str, endpoint: str) -> dict:
    """Helper to fetch data from the challenge API."""
    url = f"{api_base.rstrip('/')}/{endpoint.lstrip('/')}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def hour_to_int(time_str: str) -> int:
    return int(time_str.split(':')[0])

def int_to_hour(hour_int: int) -> str:
    return f"{hour_int:02d}:00"

def get_busy_hours(time_blocks: List[List[str]]) -> set:
    """Converts [['08:00', '11:00']] into a set of busy hours {8, 9, 10}."""
    busy = set()
    for start, end in time_blocks:
        for h in range(hour_to_int(start), hour_to_int(end)):
            busy.add(h)
    return busy

def parse_inbox_for_day(inbox_text: str, target_day: str) -> Tuple[List[List[str]], List[List[str]]]:
    """Extracts ACCEPTED and TENTATIVE time blocks for a specific day."""
    accepted = []
    tentative = []
    
    messages = inbox_text.split("From: ")
    for msg in messages:
        if not msg.strip():
            continue
            
        resp_match = re.search(r"Response:\s*(ACCEPTED|TENTATIVE|DECLINED)", msg)
        if not resp_match or resp_match.group(1) == "DECLINED":
            continue
            
        response = resp_match.group(1)
        when_match = re.search(r"When:\s*([A-Za-z]+)\s*(\d{2}:\d{2})-(\d{2}:\d{2})", msg)
        
        if when_match:
            day, start, end = when_match.groups()
            if day.lower() == target_day.lower():
                block = [start, end]
                if response == "ACCEPTED":
                    accepted.append(block)
                elif response == "TENTATIVE":
                    tentative.append(block)
                    
    return accepted, tentative

def calculate_manhattan(p1: List[int], p2: List[int]) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def get_optimal_meeting_point(positions: List[List[int]]) -> List[int]:
    """Finds the geometric median for Manhattan distance."""
    xs = sorted([p[0] for p in positions])
    ys = sorted([p[1] for p in positions])
    return [xs[len(xs) // 2], ys[len(ys) // 2]]

def get_best_outing_route(friend_positions: List[List[int]], android_pos: List[int], valid_venues: List[dict]) -> Tuple[List[int], str]:
    """Scores all 100 cells to find the absolute minimum total travel."""
    all_positions = friend_positions + [android_pos]
    best_cost = float('inf')
    best_meeting_point = None
    best_venue = None
    
    for x in range(10):
        for y in range(10):
            meeting_pt = [x, y]
            inbound_cost = sum(calculate_manhattan(p, meeting_pt) for p in all_positions)
            
            for venue in valid_venues:
                venue_pt = [venue['x'], venue['y']]
                outbound_cost = calculate_manhattan(meeting_pt, venue_pt)
                total_cost = inbound_cost + outbound_cost
                
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_meeting_point = meeting_pt
                    best_venue = venue['name']
                    
    return best_meeting_point, best_venue
