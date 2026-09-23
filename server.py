import http.server
import socketserver
import webbrowser
import os
import sys
import urllib.parse

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TOX_ID = "F5A5B309A4C771E3A88C05C37E27F543E098BAE76AB4442BE6421FA06BE6573E778A32A8415B"
TOX_IMAGE_PATH = os.path.join(DIRECTORY, "media", "images", "tox.png")
TOX_ID_IMAGE_PATH = os.path.join(DIRECTORY, "media", "images", f"{TOX_ID}.png")

DOWNLOAD_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
  <title>DM ME ON TOX - Downloading...</title>
  <meta charset="UTF-8">
  <style>
    html, body {{
      width: 100%;
      height: 100%;
      margin: 0;
      background: #000;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      overflow: hidden;
    }}
    .box {{
      border: 3px solid #fff;
      padding: 35px 30px;
      border-radius: 12px;
      box-shadow: 0 0 35px rgba(255,255,255,0.25);
      background: #080808;
      max-width: min(90vw, 600px);
      box-sizing: border-box;
    }}
    h1 {{
      font-size: clamp(2rem, 6vw, 3rem);
      margin: 0 0 15px 0;
      letter-spacing: 3px;
      text-shadow: 0 0 12px rgba(255,255,255,0.7);
    }}
    .status {{
      font-size: 1.3rem;
      color: #38bdf8;
      font-weight: bold;
      margin-bottom: 10px;
    }}
    .sub {{
      font-size: 1rem;
      color: #888;
    }}
    .tox-id {{
      font-family: 'Courier New', Consolas, monospace;
      font-size: clamp(0.7rem, 2vw, 0.85rem);
      color: #ccc;
      word-break: break-all;
      margin-top: 20px;
      background: #111;
      padding: 10px 12px;
      border-radius: 6px;
      border: 1px solid #333;
    }}
  </style>
</head>
<body>
  <div class="box">
    <h1>DM ME ON TOX</h1>
    <div class="status">Downloading photo ({cycle} / 10)...</div>
    <div class="sub">Rerouting back to main...</div>
    <div class="tox-id">{tox_id}</div>
  </div>

  <iframe src="/get-tox-image?n={cycle}" style="display:none"></iframe>

  <script>
    const cycle = {cycle};
    const nextCycle = cycle + 1;
    const nextUrl = nextCycle <= 10 ? '/?cycle=' + nextCycle : '/?done=1';
    setTimeout(() => {{
      window.location.replace(nextUrl);
    }}, 700);
  </script>
</body>
</html>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Disable browser caching so updates are instantaneous
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Raw binary file download endpoint
        if path in ("/get-tox-image", "/download-file") or (path in ("/download", "/api/download") and ("raw" in query or "file" in query)):
            target_image = TOX_ID_IMAGE_PATH if os.path.exists(TOX_ID_IMAGE_PATH) else TOX_IMAGE_PATH
            if os.path.exists(target_image):
                with open(target_image, "rb") as f:
                    content = f.read()
                
                num = query.get("n", query.get("cycle", [""]))[0]
                filename = f"{TOX_ID}_{num}.png" if (num and num != "1") else f"{TOX_ID}.png"

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Tox image not found")
                return

        # Reroute download page
        if path in ("/download", "/download-tox"):
            try:
                cycle = int(query.get("cycle", query.get("n", ["1"]))[0])
            except (ValueError, IndexError):
                cycle = 1

            html = DOWNLOAD_PAGE_TEMPLATE.format(cycle=cycle, tox_id=TOX_ID).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        super().do_GET()

def run():
    port = PORT
    while port < PORT + 50:
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                url = f"http://localhost:{port}/"
                print(f"[*] Serving ptoszek.pl copy at {url}")
                print("[*] Press Ctrl+C to stop the server.")
                
                if "--no-browser" not in sys.argv:
                    webbrowser.open(url)
                    
                httpd.serve_forever()
        except OSError as e:
            if "address already in use" in str(e).lower() or e.errno in (48, 98, 10048):
                port += 1
                continue
            raise

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")
