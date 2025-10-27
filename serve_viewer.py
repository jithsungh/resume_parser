#!/usr/bin/env python3
"""
Simple HTTP server to view the resume segmentation viewer.
Handles CORS for PDF.js and serves both the viewer and resume files.

Usage:
    python serve_viewer.py [--port 8000] [--host localhost]
"""

import argparse
import http.server
import socketserver
import os
import sys
from pathlib import Path


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS support for PDF.js"""
    
    def end_headers(self):
        """Add CORS headers to allow PDF.js to load files"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    parser = argparse.ArgumentParser(description='Serve Resume Viewer with CORS support')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on (default: 8000)')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--dir', help='Directory to serve (default: current directory)')
    
    args = parser.parse_args()
    
    # Change to specified directory or project root
    if args.dir:
        os.chdir(args.dir)
    else:
        # Change to project root (where viewer.html is)
        project_root = Path(__file__).parent
        os.chdir(project_root)
    
    print(f"\n{'='*60}")
    print(f"  Resume Viewer Server")
    print(f"{'='*60}")
    print(f"  Serving from: {os.getcwd()}")
    print(f"  URL: http://{args.host}:{args.port}/viewer.html")
    print(f"{'='*60}\n")
    print("📁 Available viewers:")
    print(f"   - Main Viewer:   http://{args.host}:{args.port}/viewer.html")
    print(f"   - Batch Viewer:  http://{args.host}:{args.port}/scripts/index.html")
    print(f"\n📋 To test with batch results:")
    print(f"   1. Run: python segment_batch.py <resume_folder> --output results.json")
    print(f"   2. Open viewer and load results.json")
    print(f"\n⌨️  Press Ctrl+C to stop the server\n")
    
    try:
        with socketserver.TCPServer((args.host, args.port), CORSRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Error: Port {args.port} is already in use!")
            print(f"   Try a different port: python serve_viewer.py --port {args.port + 1}")
        else:
            print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
