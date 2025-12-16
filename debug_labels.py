import requests

repo = "ckeditor/ckeditor5"
url = f"https://api.github.com/repos/{repo}/labels"
params = {
    "per_page": 100
}

print(f"Fetching labels from {url}...")
response = requests.get(url, params=params)

if response.status_code == 200:
    labels = response.json()
    print(f"Found {len(labels)} labels.")
    for l in labels:
        if "access" in l['name'].lower() or "a11y" in l['name'].lower() or "wcag" in l['name'].lower():
            print(f"MATCH: {l['name']}")
else:
    print(response.status_code)
