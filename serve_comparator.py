import os
import json
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
import pandas as pd

app = Flask(__name__)
RESULTS_DIR = Path('results')

# Utility: Parse run folder name into repo, model, date

def parse_run_folder(folder_name):
    parts = folder_name.split('-')
    if len(parts) < 3:
        return None
    repo = parts[0]
    model = parts[1]
    date = '-'.join(parts[2:])
    return {'repo': repo, 'model': model, 'date': date, 'folder': folder_name}

@app.route('/api/scans')
def list_scans():
    scans = []
    for folder in RESULTS_DIR.iterdir():
        if folder.is_dir():
            meta = parse_run_folder(folder.name)
            if meta:
                scans.append(meta)
    return jsonify(scans)

@app.route('/api/comparison')
def get_comparison():
    # Accept repo, model, date as query params (comma-separated for multi)
    repo = request.args.get('repo')
    model = request.args.get('model')
    date = request.args.get('date')
    # Support multiple selections
    selected = []
    for folder in RESULTS_DIR.iterdir():
        if folder.is_dir():
            meta = parse_run_folder(folder.name)
            if not meta:
                continue
            if repo and meta['repo'] not in repo.split(','):
                continue
            if model and meta['model'] not in model.split(','):
                continue
            if date and meta['date'] not in date.split(','):
                continue
            selected.append((meta, folder))
    # For each selected scan, load the latest issues_summarized_*.csv
    comparison_items = {}
    for meta, folder in selected:
        csvs = sorted(folder.glob('issues_summarized_*.csv'))
        if not csvs:
            continue
        df = pd.read_csv(csvs[-1])
        for _, row in df.iterrows():
            item_id = str(row.get('Issue ID', row.get('id', 'unknown')))
            if item_id not in comparison_items:
                comparison_items[item_id] = {
                    'id': item_id,
                    'context': row.get('Description', ''),
                    'source_url': row.get('Issue URL', ''),
                    'models': []
                }
            comparison_items[item_id]['models'].append({
                'model_name': f"{meta['repo']}-{meta['model']}-{meta['date']}",
                'text': row.get('acr_note', row.get('thread_tldr', ''))
            })
    # Output as a list
    return jsonify(list(comparison_items.values()))

@app.route('/<path:path>')
def static_proxy(path):
    # Serve static files (comparator.html, etc.)
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
