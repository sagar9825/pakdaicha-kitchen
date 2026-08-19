import os
from flask import Flask, send_file, send_from_directory

app = Flask(__name__, static_folder=".")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    audio_path = os.path.join(os.getcwd(), "audio", filename)
    if os.path.exists(audio_path):
        # conditional=True enables HTTP 206 Byte-Range streaming for scrubbing
        return send_file(audio_path, mimetype="audio/mpeg", conditional=True)
    return "File Not Found", 404

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(".", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
