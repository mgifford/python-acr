import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import os
from functools import lru_cache

def sanitize_drupal_tag_text(field_item):
    """Extract only the visible tag label, excluding tooltip/helper text."""
    link = field_item.find('a')
    if link:
        text = link.get_text(strip=True)
        if text:
            return text

    text = field_item.get_text(separator=' ', strip=True)
    if not text:
        return ""

    lowered = text.lower()
    marker = 'about tags'
    idx = lowered.find(marker)
    if idx != -1:
        text = text[:idx]

    return text.strip()


def normalize_taxonomy_values(values):
    """Normalize taxonomy/label collections into a deduplicated pipe-delimited string."""
    if not values:
        return ""

    if isinstance(values, str):
        values = [values]

    normalized = []
    seen = set()
    for raw in values:
        if raw is None:
            continue
        text = str(raw).strip()
        if not text:
            continue
        text = text.replace('|', '/').strip()
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return "|".join(normalized)


@lru_cache(maxsize=512)
def fetch_drupal_issue_taxonomies(issue_url):
    """Fetch Drupal issue tags (taxonomies) from the issue detail page."""
    if not issue_url:
        return []

    try:
        response = requests.get(issue_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        tags = []
        seen = set()

        for field in soup.select('div.field'):
            label = field.find(class_='field-label')
            if not label:
                continue
            label_text = label.get_text(strip=True).lower()
            if 'issue tags' not in label_text:
                continue
            for item in field.select('.field-item'):
                tag_text = sanitize_drupal_tag_text(item)
                if not tag_text:
                    continue
                sanitized = tag_text.replace('|', '/').strip()
                key = sanitized.lower()
                if key in seen:
                    continue
                seen.add(key)
                tags.append(sanitized)

        return tags
    except Exception as exc:
        print(f"Warning: unable to fetch taxonomies for {issue_url}: {exc}")
        return []

def extract_github_issues(repo_full_name, tags=None, limit=50):
    print(f"Extracting GitHub issues for: {repo_full_name}")
    # repo_full_name should be "owner/repo"
    
    if tags:
        labels = [t.strip() for t in tags]
        print(f"Using custom labels: {labels}")
    else:
        labels = ["accessibility", "a11y", "wcag"]
    
    all_issues = {}
    
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    # Discover relevant labels first if no custom tags provided
    if not tags:
        print("Discovering accessibility labels...")
        labels_url = f"https://api.github.com/repos/{repo_full_name}/labels"
        try:
            l_resp = requests.get(labels_url, headers=headers, params={"per_page": 100})
            if l_resp.status_code == 200:
                repo_labels = [l['name'] for l in l_resp.json()]
                # Find labels containing keywords
                discovered = [l for l in repo_labels if any(k in l.lower() for k in ["accessibility", "a11y", "wcag"])]
                if discovered:
                    print(f"Found labels: {discovered}")
                    labels = discovered
                else:
                    print("No specific accessibility labels found. Using defaults.")
        except Exception as e:
            print(f"Warning: Could not auto-discover labels: {e}")

    for label in labels:
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo_full_name}/issues"
            params = {
                "labels": label,
                "state": "open",
                "per_page": 100, # Max per page
                "page": page
            }
            
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    print(f"Error fetching GitHub issues: {response.status_code} {response.text}")
                    if response.status_code == 403 and "rate limit" in response.text.lower():
                        print("Tip: Use --github-token <token> to increase your API rate limit.")
                    break
                
                issues = response.json()
                if not issues:
                    break
                
                for issue in issues:
                    # Skip pull requests if we only want issues
                    if "pull_request" in issue:
                        continue
                        
                    issue_id = str(issue["number"])
                    if issue_id not in all_issues:
                        issue_labels = [
                            lbl.get("name", "").strip()
                            for lbl in issue.get("labels", [])
                            if lbl.get("name")
                        ]
                        all_issues[issue_id] = {
                            "Issue ID": issue_id,
                            "Issue Title": issue["title"],
                            "Description": issue["body"] if issue["body"] else "",
                            "Issue URL": issue["html_url"],
                            "Project": repo_full_name,
                            "Status": issue["state"],
                            "Priority": "Unknown", # GitHub doesn't have standard priority field
                            "Component": "Unknown",
                            "Version": "Unknown",
                            "Created": issue["created_at"],
                            "wcag_sc": "Unknown", # We'd need to parse labels or body for this
                            "Taxonomies": normalize_taxonomy_values(issue_labels)
                        }
                
                if len(all_issues) >= limit:
                    break
                page += 1
            except Exception as e:
                print(f"Exception fetching GitHub issues: {e}")
                break
        
        if len(all_issues) >= limit:
            break
            
    print(f"Total unique GitHub issues found: {len(all_issues)}")
    return pd.DataFrame(list(all_issues.values()))

def extract_drupal_issues(project_id, tags=None, limit=50):
    print(f"Extracting issues for project: {project_id}")
    base_url = f"https://www.drupal.org/project/issues/search/{project_id}"
    
    # List of tags to search for. We'll fetch them sequentially to ensure coverage.
    # Note: Drupal.org search is inclusive, so searching for multiple tags at once might be restrictive (AND logic)
    # or permissive (OR logic) depending on the field. For tags, it's often AND.
    # So we will make separate requests and merge them.
    
    if tags:
        tags_to_search = [t.strip() for t in tags]
        print(f"Using custom tags: {tags_to_search}")
    else:
        # Base tags
        tags_to_search = ["accessibility", "a11y", "wcag"]
        
        # Generate specific SC tags (e.g., wcag111, wcag131, wcag412)
        # We include a broad range to cover A, AA, AAA for WCAG 2.0, 2.1, 2.2
        sc_list = [
            # Perceivable
            "111", "121", "122", "123", "124", "125", "126", "127", "128", "129",
            "131", "132", "133", "134", "135", "136",
            "141", "142", "143", "144", "145", "146", "147", "148", "149", "1410", "1411", "1412", "1413",
            # Operable
            "211", "212", "213", "214",
            "221", "222", "223", "224", "225", "226",
            "231", "232", "233",
            "241", "242", "243", "244", "245", "246", "247", "248", "249", "2410", "2411", "2412", "2413",
            "251", "252", "253", "254", "255", "256", "257", "258",
            # Understandable
            "311", "312", "313", "314", "315", "316",
            "321", "322", "323", "324", "325", "326",
            "331", "332", "333", "334", "335", "336", "337", "338", "339",
            # Robust
            "411", "412", "413"
        ]
        
        tags_to_search.extend([f"wcag{sc}" for sc in sc_list])
    
    all_issues = {} # Use dict with Issue ID as key to deduplicate
    error_count = 0

    def register_error():
        nonlocal error_count
        error_count += 1
        if error_count == 2:
            wait = 5
            print(f"Encountered {error_count} errors. Pausing for {wait} seconds before continuing...")
            time.sleep(wait)
        elif error_count == 5:
            wait = 30
            print(f"Encountered {error_count} errors. Pausing for {wait} seconds before continuing...")
            time.sleep(wait)
        elif error_count >= 10:
            print("Encountered 10 errors. Stopping extraction early to avoid spamming the server.")
            return True
        return False

    for tag in tags_to_search:
        params = {
            "issue_tags": tag,
            "status[]": [1, 8, 13, 14, 16], # Active statuses
            "limit": limit
        }
        
        # Retry logic
        max_retries = 3
        backoff = 5
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"Fetching issues with tag '{tag}' (Attempt {attempt+1})...")
                response = requests.get(base_url, params=params)
                
                if response.status_code == 429:
                    wait = backoff * (attempt + 1)
                    print(f"Rate limited (429). Waiting {wait} seconds...")
                    if register_error():
                        return pd.DataFrame(list(all_issues.values()))
                    time.sleep(wait)
                    continue
                    
                response.raise_for_status()
                break # Success
            except Exception as e:
                print(f"Error fetching tag '{tag}': {e}")
                if register_error():
                    return pd.DataFrame(list(all_issues.values()))
                time.sleep(1)
        
        if not response or response.status_code != 200:
            print(f"Failed to fetch tag '{tag}' after retries.")
            if register_error():
                return pd.DataFrame(list(all_issues.values()))
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
            
        table = soup.find('table', class_='project-issue')
        if not table:
            continue

        rows = table.find('tbody').find_all('tr')
        
        # Parse WCAG SC from tag if possible
        # tag is like "wcag111" -> "1.1.1"
        current_wcag = "Unknown"
        if tag.startswith("wcag") and tag[4:].isdigit():
            nums = tag[4:]
            if len(nums) >= 3:
                current_wcag = f"{nums[0]}.{nums[1]}.{nums[2:]}"
        elif tag in ["accessibility", "a11y", "wcag"]:
            current_wcag = "General"
        
        for row in rows:
            try:
                title_link = row.find('td', class_='views-field-title').find('a')
                title = title_link.text.strip()
                link = 'https://www.drupal.org' + title_link['href']
                issue_id = link.split('/')[-1]
                
                if issue_id in all_issues:
                    # Update WCAG if we found a more specific one
                    if all_issues[issue_id]["wcag_sc"] in ["Unknown", "General"] and current_wcag not in ["Unknown", "General"]:
                         all_issues[issue_id]["wcag_sc"] = current_wcag
                    continue 

                # Safe extraction of fields
                def get_text(class_name):
                    el = row.find('td', class_=class_name)
                    return el.text.strip() if el else "Unknown"

                status = get_text('views-field-field-issue-status')
                priority = get_text('views-field-field-issue-priority')
                component = get_text('views-field-field-issue-component')
                version = get_text('views-field-field-issue-version')
                created = get_text('views-field-created')
                
                description = title 

                issue_tags = fetch_drupal_issue_taxonomies(link)
                normalized_tag = tag.replace('|', '/').strip() if tag else ""
                if normalized_tag:
                    normalized_lower = normalized_tag.lower()
                    if not any(existing.lower() == normalized_lower for existing in issue_tags):
                        issue_tags.append(normalized_tag)

                all_issues[issue_id] = {
                    "Issue ID": issue_id,
                    "Issue Title": title,
                    "Description": description, 
                    "Issue URL": link,
                    "Project": project_id,
                    "Status": status,
                    "Priority": priority,
                    "Component": component,
                    "Version": version,
                    "Created": created,
                    "wcag_sc": current_wcag,
                    "Taxonomies": normalize_taxonomy_values(issue_tags)
                }
                
            except Exception as e:
                continue
        
        # Be nice to the server
        time.sleep(1)

    print(f"Total unique issues found: {len(all_issues)}")
    return pd.DataFrame(list(all_issues.values()))

def run(project_id, repo_id, results_dir, tags=None, limit=None):
    # repo_id is passed from argparse, usually same as project_id or 'drupal'
    if repo_id and "/" in repo_id:
        df = extract_github_issues(repo_id, tags=tags)
    else:
        df = extract_drupal_issues(repo_id if repo_id else 'drupal', tags=tags)
    
    # Apply limit if specified
    if limit and not df.empty:
        print(f"Limiting to first {limit} issues (out of {len(df)} total)")
        df = df.head(limit)
    
    if not df.empty:
        timestamp = datetime.now().strftime('%Y%m%d')
        outfile = results_dir / f"issues_raw_{timestamp}.csv"
        df.to_csv(outfile, index=False)
        print(f"Saved {len(df)} issues to {outfile}")
    else:
        print("No issues extracted.")
