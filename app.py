from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path

POD_NAME = os.environ.get("POD_NAME", "unknown")
READY_FILE = Path("/tmp/unready")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ready":
            ready = not READY_FILE.exists()
            self.send_response(200 if ready else 503)
            self.end_headers()
            self.wfile.write(b"ready\n" if ready else b"not ready\n")
            return
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"alive\n")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"inventory response from {POD_NAME}\n".encode())

    def log_message(self, fmt, *args):
        print(f"{POD_NAME} - {fmt % args}", flush=True)

HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
