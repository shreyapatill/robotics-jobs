import requests
import json
import re

company = "ReflexRobotics"
url = f"https://jobs.ashbyhq.com/{company}"
response = requests.get(url)
print(f"Status: {response.status_code}")

# Save to file for inspection
with open("ashby_response.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("Saved to ashby_response.html")

# Look for job posting IDs and titles
# Pattern like: "id":"abc123","title":"Software Engineer"
pattern = r'"id"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]+)"'
matches = re.findall(pattern, response.text)
if matches:
    print(f"\nFound {len(matches)} potential jobs:")
    for id, title in matches[:10]:
        print(f"  - {title} (ID: {id})")

# Also try: "title":"...",..."id":"..." pattern
pattern2 = r'"title"\s*:\s*"([^"]+)"[^}]*"id"\s*:\s*"([^"]+)"'
matches2 = re.findall(pattern2, response.text)
if matches2:
    print(f"\nAlternate pattern found {len(matches2)} jobs:")
    for title, id in matches2[:10]:
        print(f"  - {title} (ID: {id})")
