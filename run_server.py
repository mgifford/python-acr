import http.server
import socketserver
import os
import json
import glob
from urllib.parse import urlparse, parse_qs

PORT = 8000
# Default fallback
DEFAULT_DATA_FILE = "results/12-12-2025/issues_summarized_20251212.csv"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # API to list available datasets
        if parsed_path.path == '/api/datasets':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            files = []
            # Look for thread analyzed files first, then summarized issues
            for file_path in glob.glob("results/**/issues_thread_analyzed_*.csv", recursive=True):
                files.append(file_path)
            
            # If no thread analyzed files, fall back to summarized
            if not files:
                for file_path in glob.glob("results/**/issues_summarized_*.csv", recursive=True):
                    files.append(file_path)
            
            # Sort files to show newest first (by modification time or name)
            files.sort(key=os.path.getmtime, reverse=True)
            
            self.wfile.write(json.dumps(files).encode())
            return

        # API to load a specific dataset
        if parsed_path.path == '/data/load':
            query_params = parse_qs(parsed_path.query)
            requested_file = query_params.get('file', [None])[0]
            
            target_file = requested_file if requested_file else DEFAULT_DATA_FILE
            
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
