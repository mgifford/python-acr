import requests
import os

repo = "ckeditor/ckeditor5"
url = f"https://api.github.com/repos/{repo}/issues"
params = {
    "state": "open",
    "per_page": 5
}
headers = {
    "Accept": "application/vnd.github.v3+json"
}

print(f"Fetching from {url}...")
response = requests.get(url, headers=headers, params=params)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    issues = response.json()
    print(f"Found {len(issues)} issues (generic search).")
    if len(issues) > 0:
        print("First issue labels:")
        for label in issues[0]['labels']:
            print(f" - {label['name']}")
else:
    print(response.text)

# Test with specific label
label = "accessibility"
params['labels'] = label
print(f"\nFetching with label='{label}'...")
response = requests.get(url, headers=headers, params=params)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    issues = response.json()
    print(f"Found {len(issues)} issues with label '{label}'.")
else:
    print(response.text)
