import requests

# Test with similar headers to the scraper
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

url = "https://jobs.ashbyhq.com/ReflexRobotics"

# Test 1: With full headers
print("Test 1: With Accept-Encoding gzip")
response1 = requests.get(url, headers=headers, timeout=30)
print(f"  Status: {response1.status_code}, Length: {len(response1.text)}")

# Test 2: Without Accept-Encoding
print("\nTest 2: Without Accept-Encoding")
headers2 = headers.copy()
del headers2["Accept-Encoding"]
response2 = requests.get(url, headers=headers2, timeout=30)
print(f"  Status: {response2.status_code}, Length: {len(response2.text)}")

# Test 3: Minimal headers
print("\nTest 3: Minimal headers")
response3 = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
print(f"  Status: {response3.status_code}, Length: {len(response3.text)}")

# Check regex match count
import re
pattern = r'"id"\s*:\s*"([a-f0-9-]{36})"\s*,\s*"title"\s*:\s*"([^"]+)"'
for i, r in enumerate([response1, response2, response3], 1):
    matches = len(re.findall(pattern, r.text))
    print(f"  Response {i}: {matches} job matches")
