from flask import Flask, Response
import subprocess
import threading
import os
import traceback
from datetime import datetime

app = Flask(__name__)

# =========================================================
# CHANNELS
# =========================================================

YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/@mediaoneTVlive/live",
    "lofi": "https://www.youtube.com/@LofiGirl/live",
    "nasa": "https://www.youtube.com/@NASA/live"
}

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

PROXY = os.getenv("PROXY_URL", "").strip()

COOKIES_FILE = os.getenv(
    "COOKIES_FILE",
    "/mnt/data/cookies.txt"
)

# =========================================================
# STARTUP LOGS
# =========================================================

print("\n========================================")
print("YOUTUBE AUDIO STREAM SERVER STARTING")
print("========================================")

print(f"[BOOT] Time: {datetime.now()}")

print(f"[BOOT] PROXY RAW = {repr(PROXY)}")

print(f"[BOOT] COOKIES FILE = {COOKIES_FILE}")

print(f"[BOOT] COOKIES EXISTS = {os.path.exists(COOKIES_FILE)}")

print("========================================\n")

# =========================================================
# FFMPEG SETTINGS
# =========================================================

FFMPEG_CMD = [
    "ffmpeg",

    "-loglevel", "info",

    "-i", "pipe:0",

    "-vn",

    "-ac", "1",
    "-ar", "22050",
    "-b:a", "40k",

    "-f", "mp3",
    "-"
]

# =========================================================
# LOGGING THREAD
# =========================================================

def log_output(pipe, prefix):

    try:

        for line in iter(pipe.readline, b''):

            if not line:
                break

            try:

                decoded = line.decode(
                    errors="ignore"
                ).rstrip()

                print(f"[{prefix}] {decoded}")

            except Exception as e:

                print(f"[LOG ERROR] {e}")

    except Exception as e:

        print(f"[THREAD ERROR] {prefix}: {e}")


# =========================================================
# STREAM GENERATOR
# =========================================================

def generate_stream(url):

    print("\n================================================")
    print("[SYSTEM] NEW STREAM SESSION")
    print("================================================")

    print(f"[SYSTEM] URL = {url}")

    # =====================================================
    # BUILD YT-DLP COMMAND
    # =====================================================

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

    # =====================================================
    # COOKIES
    # =====================================================

    if os.path.exists(COOKIES_FILE):

        print(f"[SYSTEM] Using cookies: {COOKIES_FILE}")

        ytdlp_cmd += [
            "--cookies",
            COOKIES_FILE
        ]

    else:

        print("[SYSTEM] cookies.txt NOT FOUND")

    # =====================================================
    # PROXY
    # =====================================================

    if PROXY:

        print("[SYSTEM] Proxy ENABLED")

        print(f"[SYSTEM] Proxy = {PROXY}")

        ytdlp_cmd += [
            "--proxy",
            PROXY
        ]

    else:

        print("[SYSTEM] Proxy DISABLED")

    # =====================================================
    # ADD URL
    # =====================================================

    ytdlp_cmd.append(url)

    # =====================================================
    # PRINT FULL COMMAND
    # =====================================================

    print("\n[SYSTEM] yt-dlp COMMAND:")
    print(" ".join(ytdlp_cmd))

    print("\n[SYSTEM] ffmpeg COMMAND:")
    print(" ".join(FFMPEG_CMD))

    # =====================================================
    # START YT-DLP
    # =====================================================

    print("\n[SYSTEM] Starting yt-dlp...")

    try:

        ytdlp = subprocess.Popen(
            ytdlp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        print(f"[SYSTEM] yt-dlp PID = {ytdlp.pid}")

    except Exception as e:

        print("[SYSTEM] FAILED TO START yt-dlp")
        print(e)

        traceback.print_exc()

        return

    # =====================================================
    # START YT-DLP LOG THREAD
    # =====================================================

    threading.Thread(
        target=log_output,
        args=(ytdlp.stderr, "YT-DLP"),
        daemon=True
    ).start()

    # =====================================================
    # START FFMPEG
    # =====================================================

    print("\n[SYSTEM] Starting ffmpeg...")

    try:

        ffmpeg = subprocess.Popen(
            FFMPEG_CMD,
            stdin=ytdlp.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

        print(f"[SYSTEM] ffmpeg PID = {ffmpeg.pid}")

    except Exception as e:

        print("[SYSTEM] FAILED TO START ffmpeg")
        print(e)

        traceback.print_exc()

        try:
            ytdlp.kill()
        except:
            pass

        return

    # =====================================================
    # START FFMPEG LOG THREAD
    # =====================================================

    threading.Thread(
        target=log_output,
        args=(ffmpeg.stderr, "FFMPEG"),
        daemon=True
    ).start()

    # =====================================================
    # STREAM LOOP
    # =====================================================

    print("\n[SYSTEM] STREAM LOOP STARTED")

    total_bytes = 0

    while True:

        try:

            data = ffmpeg.stdout.read(1024)

            if not data:

                print("\n[SYSTEM] NO MORE AUDIO DATA")
                break

            total_bytes += len(data)

            if total_bytes % (1024 * 100) == 0:

                print(
                    f"[SYSTEM] Streamed {total_bytes} bytes"
                )

            yield data

        except Exception as e:

            print(f"\n[SYSTEM ERROR] {e}")

            traceback.print_exc()

            break

    # =====================================================
    # CLEANUP
    # =====================================================

    print("\n[SYSTEM] CLEANING UP PROCESSES")

    try:

        ytdlp.kill()

        print("[SYSTEM] yt-dlp killed")

    except Exception as e:

        print(f"[SYSTEM] yt-dlp cleanup error: {e}")

    try:

        ffmpeg.kill()

        print("[SYSTEM] ffmpeg killed")

    except Exception as e:

        print(f"[SYSTEM] ffmpeg cleanup error: {e}")

    print("[SYSTEM] SESSION ENDED")
    print("================================================\n")


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    html = """
    <html>

    <head>

        <title>YouTube Audio Streams</title>

        <style>

            body {
                background: #111;
                color: white;
                font-family: Arial;
                padding: 20px;
            }

            h1 {
                color: #00ff99;
            }

            a {
                color: #00ccff;
                text-decoration: none;
                font-size: 20px;
            }

            li {
                margin: 15px 0;
            }

            .ok {
                color: #00ff99;
            }

            .bad {
                color: red;
            }

        </style>

    </head>

    <body>

        <h1>YouTube Audio Streams</h1>
    """

    if PROXY:

        html += "<p class='ok'>Proxy ENABLED</p>"

    else:

        html += "<p class='bad'>Proxy DISABLED</p>"

    if os.path.exists(COOKIES_FILE):

        html += "<p class='ok'>cookies.txt FOUND</p>"

    else:

        html += "<p class='bad'>cookies.txt NOT FOUND</p>"

    html += "<ul>"

    for name in YOUTUBE_STREAMS:

        html += f'<li>🎧 <a href="/{name}">{name}</a></li>'

    html += """
        </ul>

        <hr>

        <a href="/health">Health</a><br><br>

        <a href="/node">Node Check</a>

    </body>

    </html>
    """

    return html


# =========================================================
# NODE CHECK
# =========================================================

@app.route("/node")
def node_check():

    try:

        version = subprocess.check_output(
            ["node", "-v"]
        ).decode().strip()

        return f"NODE OK: {version}"

    except Exception as e:

        return f"NODE FAILED: {e}"


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "running",
        "proxy_enabled": bool(PROXY),
        "proxy_value": PROXY,
        "cookies_exists": os.path.exists(COOKIES_FILE),
        "cookies_path": COOKIES_FILE,
        "channels": list(YOUTUBE_STREAMS.keys())
    }


# =========================================================
# STREAM ROUTE
# =========================================================

@app.route("/<channel>")
def stream(channel):

    print(f"\n[SYSTEM] Incoming request: {channel}")

    url = YOUTUBE_STREAMS.get(channel)

    if not url:

        print("[SYSTEM] Channel NOT FOUND")

        return "Channel not found", 404

    print(f"[SYSTEM] Streaming URL: {url}")

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("[SYSTEM] Flask app starting")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        threaded=True
    )
