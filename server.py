import os, sys, re, subprocess, http.server, socketserver, urllib.parse, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "audio_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Find yt-dlp binary
YTDLP = "yt-dlp"
local_ytdlp = os.path.join(os.path.expanduser('~'), r'AppData\Local\Python\pythoncore-3.14-64\Scripts\yt-dlp.exe')
if os.path.exists(local_ytdlp):
    YTDLP = local_ytdlp

def extract_yt_id(url):
    m = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return m.group(1) if m else ''

def get_audio_filepath(yt_id):
    """Returns path to cached audio file or downloads it on-demand."""
    cached_file = os.path.join(CACHE_DIR, f"{yt_id}.m4a")
    if os.path.exists(cached_file) and os.path.getsize(cached_file) > 100000:
        return cached_file

    print(f"[*] On-demand streaming/caching: {yt_id} ...", flush=True)
    
    cmd = [
        YTDLP,
        '--no-playlist',
        '--extractor-args', 'youtube:player_client=android,ios',
        '-f', 'ba[ext=m4a]/ba/b[ext=mp4]/b',
        '--no-check-certificates',
        '-o', cached_file,
        f"https://www.youtube.com/watch?v={yt_id}"
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
        if r.returncode == 0 and os.path.exists(cached_file) and os.path.getsize(cached_file) > 10000:
            print(f"[+] Successfully cached {yt_id} ({os.path.getsize(cached_file)} bytes)", flush=True)
            return cached_file
        else:
            print(f"[-] yt-dlp error for {yt_id}: {r.stderr[:200]}", flush=True)
    except Exception as e:
        print(f"[-] Download exception for {yt_id}: {e}", flush=True)
    return None

class YTAudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # Audio Streaming Endpoint
        if parsed.path in ('/api/stream', '/api/audio'):
            qs = urllib.parse.parse_qs(parsed.query)
            yt_id = qs.get('v', qs.get('id', ['']))[0]
            
            if not yt_id:
                self.send_error(400, "Missing 'v' parameter")
                return
            
            filepath = get_audio_filepath(yt_id)
            if not filepath or not os.path.exists(filepath):
                self.send_error(502, "Could not fetch audio stream from YouTube")
                return
            
            file_size = os.path.getsize(filepath)
            range_header = self.headers.get('Range')
            
            start = 0
            end = file_size - 1
            status_code = 200
            
            if range_header:
                match = re.search(r'bytes=(\d+)-(\d*)', range_header)
                if match:
                    start = int(match.group(1))
                    if match.group(2):
                        end = int(match.group(2))
                    status_code = 206
            
            content_length = (end - start) + 1
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'audio/mp4')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(content_length))
            if status_code == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            
            try:
                with open(filepath, 'rb') as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk_size = min(64 * 1024, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (ConnectionResetError, BrokenPipeError):
                pass
            return

        # Default static file serving
        return super().do_GET()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), YTAudioHandler) as httpd:
        print(f"Pakdaicha Server running at http://0.0.0.0:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
