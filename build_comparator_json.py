import os
import json
import math
from pathlib import Path
import pandas as pd
import argparse

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = BASE_DIR / 'results'


def safe(value):
    """Return a JSON-safe string, trimming NaN/None values."""
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    if isinstance(value, str):
        return value.strip()
    if pd.isna(value):
        return ''
    return str(value)

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
def build_comparison(results_dir=DEFAULT_RESULTS_DIR):
    results_dir = Path(results_dir)
    summary_path = results_dir / 'projects_with_multiple_runs.json'
    output_path = results_dir / 'comparison.json'
    output_path.parent.mkdir(exist_ok=True)
    # Scan all result folders and group by project/repo
    from collections import defaultdict
    all_runs = []
    project_runs = defaultdict(list)
    if not results_dir.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")
    for folder in results_dir.iterdir():
        if folder.is_dir():
            meta = parse_run_folder(folder.name)
            if meta:
                all_runs.append((meta, folder))
                project_runs[meta['repo']].append(meta)

    # Only keep projects with more than one run
    multi_run_projects = {repo: runs for repo, runs in project_runs.items() if len(runs) > 1}

    # Write summary file for UI selection
    with open(summary_path, 'w') as f:
        json.dump(multi_run_projects, f, indent=2)
    print(f"Project summary written to {summary_path}")

    # For each scan, load the latest issues_summarized_*.csv, but only for multi-run projects
    selected = [(meta, folder) for meta, folder in all_runs if meta['repo'] in multi_run_projects]
    comparison_items = {}
    for meta, folder in selected:
        thread_csvs = sorted(folder.glob('issues_thread_analyzed_*.csv'))
        summary_csvs = sorted(folder.glob('issues_summarized_*.csv'))
        source_csvs = thread_csvs or summary_csvs
        if not source_csvs:
            continue
        latest_csv = source_csvs[-1]
        try:
            csv_path = '/' + str(latest_csv.relative_to(BASE_DIR)).replace(os.sep, '/')
        except ValueError:
            csv_path = f"/results/{folder.name}/{latest_csv.name}"
        df = pd.read_csv(latest_csv)
        for _, row in df.iterrows():
            issue_id = safe(row.get('Issue ID', row.get('id', 'unknown')))
            project = safe(row.get('Project', meta['repo'])) or meta['repo']
            item_key = f"{project}::{issue_id}"
            if item_key not in comparison_items:
                comparison_items[item_key] = {
                    'id': issue_id,
                    'project': project,
                    'title': safe(row.get('Issue Title', '')),
                    'context': safe(row.get('Description', '')),
                    'description': safe(row.get('Description', '')),
                    'source_url': safe(row.get('Issue URL', '')),
                    'status': safe(row.get('Status', '')),
                    'priority': safe(row.get('Priority', '')),
                    'component': safe(row.get('Component', '')),
                    'version': safe(row.get('Version', '')),
                    'created': safe(row.get('Created', '')),
                    'wcag_sc': safe(row.get('wcag_sc', '')),
                    'models': []
                }
            comparison_items[item_key]['models'].append({
                'model_name': f"{meta['repo']}-{meta['model']}-{meta['date']}",
                'model': meta['model'],
                'run_date': meta['date'],
                'text': safe(row.get('acr_note', row.get('thread_tldr', ''))),
                'acr_note': safe(row.get('acr_note', '')),
                'dev_note': safe(row.get('dev_note', '')),
                'ai_wcag': safe(row.get('ai_wcag', '')),
                'thread_tldr': safe(row.get('thread_tldr', '')),
                'thread_problem': safe(row.get('thread_problem', '')),
                'thread_sentiment': safe(row.get('thread_sentiment', '')),
                'thread_timeline': safe(row.get('thread_timeline', '')),
                'thread_links': safe(row.get('thread_links', '')),
                'thread_journey': safe(row.get('thread_journey', '')),
                'thread_todo': safe(row.get('thread_todo', '')),
                'csv_path': csv_path
            })
    # Output as a list
    sorted_items = sorted(
        comparison_items.values(),
        key=lambda item: (item.get('project', ''), item.get('id', ''))
    )
    with open(output_path, 'w') as f:
        json.dump(sorted_items, f, indent=2)
    print(f"Comparison JSON written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Build comparison JSON for comparison.html.\nIf no options are provided this script will scan results/ and write results/comparison.json.'
    )
    parser.add_argument('--results-dir', default=str(DEFAULT_RESULTS_DIR), help='Path to the results directory')
    args = parser.parse_args()

    # Informative help when run without arguments
    if os.environ.get('CI') is None and not any(arg.startswith('-') for arg in os.sys.argv[1:]):
        print('Scanning results directory and building comparison JSON (this may take a moment).')

    build_comparison(args.results_dir)


if __name__ == '__main__':
    main()
