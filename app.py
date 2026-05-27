from flask import Flask, Response
import subprocess
import threading
import os

app = Flask(__name__)

# ==========================================
# CHANNELS
# ==========================================

YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@mediaoneTVlive/live",
    "lofi": "https://www.youtube.com/@LofiGirl/live",
    "nasa": "https://www.youtube.com/@NASA/live"
}

# ==========================================
# ENV VARIABLES
# ==========================================

PROXY = os.getenv("PROXY_URL", "").strip()

COOKIES_FILE = os.getenv(
    "COOKIES_FILE",
    "/mnt/data/cookies.txt"
)

print("===================================")
print("PROXY RAW =", repr(PROXY))
print("COOKIES =", COOKIES_FILE)
print("===================================")

# ==========================================
# FFMPEG
# ==========================================

FFMPEG_CMD = [
    "ffmpeg",
    "-loglevel", "error",

    "-i", "pipe:0",

    "-vn",

    "-ac", "1",
    "-ar", "22050",
    "-b:a", "40k",

    "-f", "mp3",
    "-"
]


# ==========================================
# LOGGING
# ==========================================

def log_output(pipe, prefix):

    for line in iter(pipe.readline, b''):

        try:
            print(f"[{prefix}] {line.decode(errors='ignore').rstrip()}")

        except Exception as e:
            print(f"[LOG ERROR] {e}")


# ==========================================
# STREAM
# ==========================================

def generate_stream(url):

    ytdlp_cmd = [
        "yt-dlp",

        "-v",

        "-f",
        "bestaudio/best",

        "-o",
        "-",

        "--no-warnings",

        "--extractor-args",
        "youtube:player_client=tv_embedded,web",

        "--live-from-start"
    ]

    # ==========================================
    # COOKIES
    # ==========================================

    if os.path.exists(COOKIES_FILE):

        print("[SYSTEM] Using cookies")

        ytdlp_cmd += [
            "--cookies",
            COOKIES_FILE
        ]

    else:

        print("[SYSTEM] cookies.txt NOT FOUND")

    # ==========================================
    # PROXY
    # ==========================================

    if PROXY:

        print("[SYSTEM] Proxy ENABLED")

        ytdlp_cmd += [
            "--proxy",
            PROXY
        ]

    else:

        print("[SYSTEM] Proxy DISABLED")

    # ==========================================
    # URL
    # ==========================================

    ytdlp_cmd.append(url)

    print("[SYSTEM] Starting yt-dlp")
    print(" ".join(ytdlp_cmd))

    # ==========================================
    # START YT-DLP
    # ==========================================

    ytdlp = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    threading.Thread(
        target=log_output,
        args=(ytdlp.stderr, "YT-DLP"),
        daemon=True
    ).start()

    # ==========================================
    # START FFMPEG
    # ==========================================

    ffmpeg = subprocess.Popen(
        FFMPEG_CMD,
        stdin=ytdlp.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    threading.Thread(
        target=log_output,
        args=(ffmpeg.stderr, "FFMPEG"),
        daemon=True
    ).start()

    # ==========================================
    # STREAM LOOP
    # ==========================================

    while True:

        try:

            data = ffmpeg.stdout.read(1024)

            if not data:
                print("[SYSTEM] Stream ended")
                break

            yield data

        except Exception as e:

            print("[SYSTEM ERROR]", e)
            break

    print("[SYSTEM] Cleaning up")

    try:
        ytdlp.kill()
    except:
        pass

    try:
        ffmpeg.kill()
    except:
        pass


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    html = """
    <html>

    <head>

    <title>YouTube Audio Streams</title>

    <style>

    body{
        background:#111;
        color:white;
        font-family:Arial;
        padding:20px;
    }

    a{
        color:#00ccff;
        font-size:20px;
        text-decoration:none;
    }

    li{
        margin:15px 0;
    }

    </style>

    </head>

    <body>

    <h1>Available Streams</h1>

    <ul>
    """

    for name in YOUTUBE_STREAMS:

        html += f'<li><a href="/{name}">{name}</a></li>'

    html += """
    </ul>

    </body>
    </html>
    """

    return html


# ==========================================
# NODE CHECK
# ==========================================

@app.route("/node")
def node_check():

    try:

        version = subprocess.check_output(
            ["node", "-v"]
        ).decode().strip()

        return f"NODE OK: {version}"

    except Exception as e:

        return f"NODE FAILED: {e}"


# ==========================================
# HEALTH
# ==========================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "proxy_enabled": bool(PROXY),
        "cookies_exists": os.path.exists(COOKIES_FILE),
        "channels": list(YOUTUBE_STREAMS.keys())
    }


# ==========================================
# STREAM ROUTE
# ==========================================

@app.route("/<channel>")
def stream(channel):

    print("[SYSTEM] Incoming request:", channel)

    url = YOUTUBE_STREAMS.get(channel)

    if not url:
        return "Channel not found", 404

    print("[SYSTEM] Streaming URL:", url)

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        threaded=True
    )
