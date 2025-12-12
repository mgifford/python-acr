import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re

def extract_drupal_issues(project_id, limit=50):
    print(f"Extracting issues for project: {project_id}")
    base_url = f"https://www.drupal.org/project/issues/search/{project_id}"
    
    # List of tags to search for. We'll fetch them sequentially to ensure coverage.
    # Note: Drupal.org search is inclusive, so searching for multiple tags at once might be restrictive (AND logic)
    # or permissive (OR logic) depending on the field. For tags, it's often AND.
    # So we will make separate requests and merge them.
    
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

    for tag in tags_to_search:
        params = {
            "issue_tags": tag,
            "status[]": [1, 8, 13, 14, 16], # Active statuses
            "limit": limit
        }
        
        try:
            print(f"Fetching issues with tag '{tag}'...")
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            table = soup.find('table', class_='project-issue')
            if not table:
                continue

            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                try:
                    title_link = row.find('td', class_='views-field-title').find('a')
                    title = title_link.text.strip()
                    link = 'https://www.drupal.org' + title_link['href']
                    issue_id = link.split('/')[-1]
                    
                    if issue_id in all_issues:
                        continue # Skip duplicates

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
                        "wcag_sc": "Unknown"
                    }
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Failed to fetch tag '{tag}': {e}")
            continue

    print(f"Total unique issues found: {len(all_issues)}")
    return pd.DataFrame(list(all_issues.values()))

def run(project_id, repo_id, results_dir):
    # repo_id is passed from argparse, usually same as project_id or 'drupal'
    df = extract_drupal_issues(repo_id if repo_id else 'drupal')
    
    if not df.empty:
        timestamp = datetime.now().strftime('%Y%m%d')
        outfile = results_dir / f"issues_raw_{timestamp}.csv"
        df.to_csv(outfile, index=False)
        print(f"Saved {len(df)} issues to {outfile}")
    else:
        print("No issues extracted.")
