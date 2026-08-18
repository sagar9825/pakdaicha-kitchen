import os, sys, re, urllib.request, urllib.parse, subprocess, http.server, socketserver

BASE = os.path.dirname(os.path.abspath(__file__))
YTDLP = "yt-dlp"

# Cache extracted streaming URLs
url_cache = {}

def get_direct_stream_url(yt_id):
    if yt_id in url_cache:
        return url_cache[yt_id]
    
    cmd = [
        YTDLP,
        '--no-playlist',
        '--extractor-args', 'youtube:player_client=android',
        '-f', 'ba/b',
        '-g',
        f"https://www.youtube.com/watch?v={yt_id}"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            stream_url = r.stdout.strip().split('\n')[0]
            url_cache[yt_id] = stream_url
            return stream_url
    except Exception as e:
        print(f"Error extracting stream for {yt_id}: {e}")
    return None

class YTAudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # Audio Streaming API endpoint
        if parsed.path in ('/api/stream', '/api/audio'):
            qs = urllib.parse.parse_qs(parsed.query)
            yt_id = qs.get('v', qs.get('id', ['']))[0]
            
            if not yt_id:
                self.send_error(400, "Missing video id parameter 'v'")
                return
            
            direct_url = get_direct_stream_url(yt_id)
            if not direct_url:
                self.send_error(404, "Could not resolve audio stream from YouTube")
                return
            
            try:
                req = urllib.request.Request(direct_url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 12; Pixel 6)')
                
                range_header = self.headers.get('Range')
                if range_header:
                    req.add_header('Range', range_header)
                
                with urllib.request.urlopen(req, timeout=12) as remote_resp:
                    status_code = remote_resp.status
                    self.send_response(status_code)
                    
                    for k, v in remote_resp.headers.items():
                        if k.lower() in ('content-type', 'content-length', 'accept-ranges', 'content-range'):
                            self.send_header(k, v)
                    
                    if 'content-type' not in [k.lower() for k in remote_resp.headers.keys()]:
                        self.send_header('Content-Type', 'audio/mp4')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    while True:
                        chunk = remote_resp.read(64 * 1024)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except (ConnectionResetError, BrokenPipeError):
                            break
            except Exception as err:
                print(f"Streaming error for {yt_id}: {err}")
                if not self.wfile.closed:
                    try:
                        self.send_error(502, f"Stream proxy error: {err}")
                    except Exception:
                        pass
            return
        
        # Default static file serving
        return super().do_GET()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), YTAudioHandler) as httpd:
        print(f"Pakdaicha YT-Audio-API Server running at http://0.0.0.0:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
