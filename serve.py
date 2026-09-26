#!/usr/bin/env python3
"""
TraceImpact 2.0 — Data Processing Control Room Server
Simple HTTP server for the demo visualization.

Usage:
    python serve.py            # Starts on port 8888
    python serve.py --port 9000  # Custom port
"""

import http.server
import os
import sys
import webbrowser

PORT = 8888

if "--port" in sys.argv:
    idx = sys.argv.index("--port")
    if idx + 1 < len(sys.argv):
        PORT = int(sys.argv[idx + 1])

# Change to demo directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map.update({
    ".js": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
})

print(f"\n  ╔══════════════════════════════════════════════════╗")
print(f"  ║  TraceImpact 2.0 — Data Processing Control Room  ║")
print(f"  ╠══════════════════════════════════════════════════╣")
print(f"  ║  http://localhost:{PORT}                          ║")
print(f"  ║                                                  ║")
print(f"  ║  Controls:                                       ║")
print(f"  ║    SPACE  — Start / Pause simulation             ║")
print(f"  ║    F      — Toggle fullscreen                    ║")
print(f"  ║    ESC    — Close overlays                       ║")
print(f"  ║                                                  ║")
print(f"  ║  Press Ctrl+C to stop                            ║")
print(f"  ╚══════════════════════════════════════════════════╝\n")

# Open browser
webbrowser.open(f"http://localhost:{PORT}")

with http.server.HTTPServer(("", PORT), handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
