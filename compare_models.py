import http.server
import socketserver
import os
import json
import csv
import argparse
import webbrowser
from functools import partial

# --- Configuration ---
PORT = 8000
OUTPUT_FILENAME = "merged_comparison_data.json"
HTML_FILENAME = "comparator.html"

def load_data(filepath):
    """Reads JSON or CSV and returns a dictionary keyed by a unique ID."""
    data_map = {}
    
    if not os.path.exists(filepath):
        print(f"❌ Error: File not found: {filepath}")
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        if filepath.endswith('.json'):
            raw_data = json.load(f)
        elif filepath.endswith('.csv'):
            reader = csv.DictReader(f)
            raw_data = list(reader)
        else:
            print(f"❌ Error: Unsupported format for {filepath}")
            return {}

    # Normalize data into a dict keyed by ID
    for item in raw_data:
        # Tries to find a common ID key.
        key = item.get('query_id') or item.get('issue_id') or item.get('id')
        if key:
            data_map[str(key)] = item
            
    return data_map

def merge_files(filepaths):
    """Merges 2 or 3 datasets into a single comparison structure."""
    datasets = []
    all_keys = set()
    
    # Load all files
    for path in filepaths:
        data = load_data(path)
        datasets.append({'name': os.path.basename(path), 'data': data})
        all_keys.update(data.keys())
    
    merged_list = []
    print(f"🔍 Merging {len(filepaths)} files with {len(all_keys)} unique items...")
    
    for key in sorted(all_keys):
        # Base entry
        merged_entry = {
            "id": key,
            "context": "No context found",
            "source_url": "",
            "models": []
        }
        
        # 1. Collect Context (Use the first valid context found across files)
        for ds in datasets:
            item = ds['data'].get(key, {})
            if not merged_entry['source_url'] and item.get('source_url'):
                merged_entry['source_url'] = item.get('source_url')
            
            # Try various common keys for context text
            ctx = item.get('context_info') or item.get('original_text') or item.get('input_data')
            if ctx and merged_entry['context'] == "No context found":
                merged_entry['context'] = ctx

        # 2. Collect Model Outputs
        for ds in datasets:
            item = ds['data'].get(key, {})
            # Try various common keys for the report output
            text = item.get('ai_generated_statement') or item.get('generated_report') or item.get('report') or "MISSING DATA"
            
            merged_entry['models'].append({
                "model_name": ds['name'], # Or item.get('model_name') if available inside file
                "text": text
            })
            
        merged_list.append(merged_entry)
        
    return merged_list

class ComparisonHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/data/comparison':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            with open(OUTPUT_FILENAME, 'rb') as f:
                self.wfile.write(f.read())
            return
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge 2-3 AI outputs and launch comparison tool.")
    parser.add_argument("files", nargs='+', help="Paths to model output files (JSON/CSV)")
    args = parser.parse_args()

    if len(args.files) < 2:
        print("⚠️  Please provide at least 2 files to compare.")
        exit(1)

    # 1. Merge Data
    merged_data = merge_files(args.files)
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2)
    
    print(f"✅ Merged data saved to {OUTPUT_FILENAME}")

    # 2. Serve
    print(f"🚀 Compare at: http://localhost:{PORT}/{HTML_FILENAME}")
    
    # Only serve files from current directory for safety
    handler = partial(ComparisonHandler, directory=os.getcwd())
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped.")
