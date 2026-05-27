import os
import subprocess
import threading
from flask import Flask, Response

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

COOKIES_FILE = "/mnt/data/cookies.txt"

# TEST FIRST WITHOUT PROXY
PROXY = None

# Example:
# PROXY = "http://user:pass@ip:port"

STREAMS = {
    "media_one": "https://www.youtube.com/@mediaoneTVlive/live",
}

# =========================================================
# LOGGING
# =========================================================

def log(prefix, message):
    print(f"[{prefix}] {message}", flush=True)

# =========================================================
# STREAM FUNCTION
# =========================================================

def generate_stream(url):

    log("SYSTEM", "=" * 50)
    log("SYSTEM", "NEW STREAM SESSION")
    log("SYSTEM", "=" * 50)

    log("SYSTEM", f"URL = {url}")
    log("SYSTEM", f"Using cookies = {COOKIES_FILE}")
    log("SYSTEM", f"Proxy enabled = {bool(PROXY)}")

    # =====================================================
    # yt-dlp command
    # IMPORTANT:
    # Using ANDROID client only
    # NO web client
    # =====================================================

    yt_cmd = [
        "yt-dlp",
        "-v",
        "-f", "bestaudio/best",
        "-o", "-",
        "--no-warnings",
        "--live-from-start",
        "--extractor-args",
        "youtube:player_client=android",
        "--cookies", COOKIES_FILE,
        url
    ]

    if PROXY:
        yt_cmd.extend(["--proxy", PROXY])

    # =====================================================
    # ffmpeg command
    # =====================================================

    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "info",

        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",

        "-i", "pipe:0",

        "-vn",

        "-ac", "1",
        "-ar", "22050",
        "-b:a", "40k",

        "-f", "mp3",
        "-"
    ]

    log("SYSTEM", "yt-dlp COMMAND:")
    log("SYSTEM", " ".join(yt_cmd))

    log("SYSTEM", "")
    log("SYSTEM", "ffmpeg COMMAND:")
    log("SYSTEM", " ".join(ffmpeg_cmd))

    # =====================================================
    # START yt-dlp
    # =====================================================

    log("SYSTEM", "")
    log("SYSTEM", "Starting yt-dlp...")

    yt_process = subprocess.Popen(
        yt_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    log("SYSTEM", f"yt-dlp PID = {yt_process.pid}")

    # =====================================================
    # START ffmpeg
    # =====================================================

    log("SYSTEM", "")
    log("SYSTEM", "Starting ffmpeg...")

    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=yt_process.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    log("SYSTEM", f"ffmpeg PID = {ffmpeg_process.pid}")

    # =====================================================
    # STDERR LOGGER
    # =====================================================

    def log_yt():
        for line in yt_process.stderr:
            try:
                log("YT-DLP", line.decode(errors="ignore").rstrip())
            except:
                pass

    def log_ffmpeg():
        for line in ffmpeg_process.stderr:
            try:
                log("FFMPEG", line.decode(errors="ignore").rstrip())
            except:
                pass

    threading.Thread(target=log_yt, daemon=True).start()
    threading.Thread(target=log_ffmpeg, daemon=True).start()

    # =====================================================
    # STREAM LOOP
    # =====================================================

    log("SYSTEM", "")
    log("SYSTEM", "STREAM LOOP STARTED")

    try:
        while True:

            chunk = ffmpeg_process.stdout.read(4096)

            if not chunk:
                log("SYSTEM", "NO MORE AUDIO DATA")
                break

            yield chunk

    except GeneratorExit:
        log("SYSTEM", "CLIENT DISCONNECTED")

    except Exception as e:
        log("SYSTEM", f"STREAM ERROR = {e}")

    finally:

        log("SYSTEM", "")
        log("SYSTEM", "CLEANING UP PROCESSES")

        try:
            yt_process.kill()
            log("SYSTEM", "yt-dlp killed")
        except:
            pass

        try:
            ffmpeg_process.kill()
            log("SYSTEM", "ffmpeg killed")
        except:
            pass

        log("SYSTEM", "SESSION ENDED")
        log("SYSTEM", "=" * 50)

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def home():
    return "YouTube Audio Stream Server Running"

@app.route("/<stream_name>")
def stream(stream_name):

    if stream_name not in STREAMS:
        return "Stream not found", 404

    url = STREAMS[stream_name]

    log("SYSTEM", "")
    log("SYSTEM", f"Incoming request: {stream_name}")
    log("SYSTEM", f"Streaming URL: {url}")

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print("")
    print("=" * 40)
    print("YOUTUBE AUDIO STREAM SERVER STARTING")
    print("=" * 40)

    print(f"[BOOT] COOKIES FILE = {COOKIES_FILE}")
    print(f"[BOOT] COOKIES EXISTS = {os.path.exists(COOKIES_FILE)}")
    print(f"[BOOT] PROXY = {PROXY}")

    print("=" * 40)
    print("")

    app.run(
        host="0.0.0.0",
        port=8000,
        threaded=True
    )
