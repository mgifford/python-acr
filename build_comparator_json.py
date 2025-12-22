import os
import json
from pathlib import Path
import pandas as pd
import argparse

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / 'results'
OUTPUT_PATH = RESULTS_DIR / 'comparison.json'
OUTPUT_PATH.parent.mkdir(exist_ok=True)

# Utility: Parse run folder name into repo, model, date
def parse_run_folder(folder_name):
    parts = folder_name.split('-')
    if len(parts) < 3:
        return None
    repo = parts[0]
    model = parts[1]
    date = '-'.join(parts[2:])
    return {'repo': repo, 'model': model, 'date': date, 'folder': folder_name}

# Scan all result folders
def build_comparison():
    # Scan all result folders and group by project/repo
    from collections import defaultdict
    all_runs = []
    project_runs = defaultdict(list)
    for folder in RESULTS_DIR.iterdir():
        if folder.is_dir():
            meta = parse_run_folder(folder.name)
            if meta:
                all_runs.append((meta, folder))
                project_runs[meta['repo']].append(meta)

    # Only keep projects with more than one run
    multi_run_projects = {repo: runs for repo, runs in project_runs.items() if len(runs) > 1}

    # Write summary file for UI selection
    summary_path = RESULTS_DIR / 'projects_with_multiple_runs.json'
    with open(summary_path, 'w') as f:
        json.dump(multi_run_projects, f, indent=2)
    print(f"Project summary written to {summary_path}")

    # For each scan, load the latest issues_summarized_*.csv, but only for multi-run projects
    selected = [(meta, folder) for meta, folder in all_runs if meta['repo'] in multi_run_projects]
    comparison_items = {}
    import math
    for meta, folder in selected:
        csvs = sorted(folder.glob('issues_summarized_*.csv'))
        if not csvs:
            continue
        latest_csv = csvs[-1]
        csv_path = f"/results/{folder.name}/{latest_csv.name}"
        df = pd.read_csv(latest_csv)
        for _, row in df.iterrows():
            item_id = str(row.get('Issue ID', row.get('id', 'unknown')))
            def safe(val):
                if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
                    return ''
                return val
            if item_id not in comparison_items:
                comparison_items[item_id] = {
                    'id': safe(item_id),
                    'context': safe(row.get('Description', '')),
                    'source_url': safe(row.get('Issue URL', '')),
                    'models': []
                }
            comparison_items[item_id]['models'].append({
                'model_name': f"{meta['repo']}-{meta['model']}-{meta['date']}",
                'text': safe(row.get('acr_note', row.get('thread_tldr', ''))),
                'csv_path': csv_path
            })
    # Output as a list
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(list(comparison_items.values()), f, indent=2)
    print(f"Comparison JSON written to {OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description='Build comparison JSON for comparison.html.\nIf no options are provided this script will scan results/ and write results/comparison.json.'
    )
    parser.add_argument('--results-dir', default=str(RESULTS_DIR), help='Path to the results directory')
    args = parser.parse_args()

    # Informative help when run without arguments
    if os.environ.get('CI') is None and not any(arg.startswith('-') for arg in os.sys.argv[1:]):
        print('Scanning results directory and building comparison JSON (this may take a moment).')

    build_comparison()


if __name__ == '__main__':
    main()
