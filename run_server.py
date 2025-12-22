import http.server
import socketserver
import os
import json
import glob
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

PORT = 8000

def get_latest_file():
    files = []
    # Look for thread analyzed files first
    for file_path in glob.glob("results/**/issues_thread_analyzed_*.csv", recursive=True):
        files.append(file_path)
    
    # If no thread analyzed files, look for summarized issues
    if not files:
        for file_path in glob.glob("results/**/issues_summarized_*.csv", recursive=True):
            files.append(file_path)
            
    if files:
        # Sort by modification time, newest first
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    return "results/12-12-2025/issues_summarized_20251212.csv" # Fallback if nothing found

# Default fallback
DEFAULT_DATA_FILE = get_latest_file()

def persist_dataset_manifest(datasets):
    """Write discoverable manifest files for the frontend fallback logic."""
    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "datasets": datasets
    }

    manifest_targets = [
        os.path.join('results', 'index.local.json'),
        os.path.join('results', 'index.json'),
        'datasets.json'
    ]

    for target in manifest_targets:
        try:
            dir_name = os.path.dirname(target)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(target, 'w', encoding='utf-8') as handle:
                json.dump(manifest, handle, indent=2)
        except Exception as exc:
            # Manifest creation should never crash the server; log and continue.
            print(f"WARNING: Unable to write manifest {target}: {exc}")

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # API to list available datasets
        if parsed_path.path == '/api/datasets':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            files = []
            # Collect ALL candidate files
            candidates = []
            candidates.extend(glob.glob("results/**/issues_thread_analyzed_*.csv", recursive=True))
            candidates.extend(glob.glob("results/**/issues_summarized_*.csv", recursive=True))
            candidates.extend(glob.glob("results/**/issues_raw_*.csv", recursive=True))
            
            # Filter candidates: Must have "Issue URL" or "source_url" in header
            file_buckets = {}
            for fpath in candidates:
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        header = f.readline()
                        if "Issue URL" in header or "source_url" in header:
                            dirname = os.path.dirname(fpath)
                            bucket = file_buckets.setdefault(dirname, {})
                            if "issues_thread_analyzed_" in fpath:
                                bucket['thread'] = fpath
                            elif "issues_summarized_" in fpath:
                                bucket['summary'] = fpath
                            elif "issues_raw_" in fpath:
                                bucket['raw'] = fpath
                except Exception:
                    continue

            # Select the best available dataset per directory (thread > summarized > raw)
            final_files = []
            for bucket in file_buckets.values():
                if 'thread' in bucket:
                    final_files.append(bucket['thread'])
                elif 'summary' in bucket:
                    final_files.append(bucket['summary'])
                elif 'raw' in bucket:
                    final_files.append(bucket['raw'])
            
            # Sort files to show newest first (by modification time)
            final_files.sort(key=os.path.getmtime, reverse=True)

            # Persist a manifest so static hosting (e.g., GitHub Pages) can discover datasets
            persist_dataset_manifest(final_files)
            
            self.wfile.write(json.dumps(final_files).encode())
            return

        # API to load a specific dataset
        if parsed_path.path == '/data/load':
            query_params = parse_qs(parsed_path.query)
            requested_file = query_params.get('file', [None])[0]
            
            target_file = requested_file if requested_file else DEFAULT_DATA_FILE
            
            print(f"DEBUG: Requested file: {requested_file}")
            print(f"DEBUG: Target file: {target_file}")
            print(f"DEBUG: Exists: {os.path.exists(target_file)}")
            
            if os.path.exists(target_file):
                # Basic security check to prevent directory traversal out of results
                if "results" not in os.path.abspath(target_file):
                     self.send_error(403, "Access denied: File must be in results directory")
                     return

                self.send_response(200)
                self.send_header('Content-type', 'text/csv')
                self.end_headers()
                with open(target_file, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {target_file}")
            return

        # Legacy endpoint for backward compatibility
        if parsed_path.path == '/data/llm_feedback_data.json':
            if os.path.exists(DEFAULT_DATA_FILE):
                self.send_response(200)
                self.send_header('Content-type', 'text/csv')
                self.end_headers()
                with open(DEFAULT_DATA_FILE, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {DEFAULT_DATA_FILE}")
            return

        super().do_GET()


print(f"Serving at http://localhost:{PORT}")
print(f"Data endpoint: http://localhost:{PORT}/data/llm_feedback_data.json")

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
