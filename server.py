import os, sys, http.server, socketserver

BASE = os.path.dirname(os.path.abspath(__file__))

class PakdaichaHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'public, max-age=86400')
        super().end_headers()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), PakdaichaHandler) as httpd:
        print(f"Pakdaicha Server running at http://0.0.0.0:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")
