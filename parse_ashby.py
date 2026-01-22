import re

with open('ashby_response.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Match job IDs with their nearby locationName
job_pattern = r'"id"\s*:\s*"([a-f0-9-]{36})"\s*,\s*"title"\s*:\s*"([^"]+)"'
matches = list(re.finditer(job_pattern, content))

print(f"Found {len(matches)} jobs:")
for match in matches:
    job_id = match.group(1)
    title = match.group(2)
    
    # Find locationName after this match
    start = match.end()
    nearby = content[start:start+1000]
    loc_match = re.search(r'"locationName"\s*:\s*"([^"]+)"', nearby)
    location = loc_match.group(1) if loc_match else "Unknown"
    
    # Check if matches our keywords
    keywords = ["robotics", "robot", "autonomous", "autonomy", "perception", "embedded", "navigation", "ROS"]
    matched = any(kw.lower() in title.lower() for kw in keywords)
    
    print(f"  {'✓' if matched else ' '} {title} | {location} | {job_id[:8]}...")
