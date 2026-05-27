from flask import Flask, Response
import subprocess
import threading
import os

app = Flask(__name__)

YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/watch?v=-8d8-c0yvyU"
}

COOKIES_FILE = "/mnt/data/cookies.txt"

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


def log_output(pipe, prefix):
    """
    Print subprocess logs in realtime
    """
    for line in iter(pipe.readline, b''):
        try:
            print(f"[{prefix}] {line.decode(errors='ignore').rstrip()}")
        except:
            pass


def generate_stream(url):

    ytdlp_cmd = [
        "yt-dlp",
        "-v",
        "-f", "bestaudio",
        "-o", "-",
        "--no-warnings",
        "--live-from-start"
    ]

    # Add cookies if available
    if os.path.exists(COOKIES_FILE):
        print(f"[SYSTEM] Using cookies: {COOKIES_FILE}")
        ytdlp_cmd += ["--cookies", COOKIES_FILE]
    else:
        print("[SYSTEM] cookies.txt not found")

    ytdlp_cmd.append(url)

    print("[SYSTEM] Starting yt-dlp...")
    print(" ".join(ytdlp_cmd))

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

    print("[SYSTEM] Starting ffmpeg...")
    print(" ".join(FFMPEG_CMD))

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

    while True:
        try:
            data = ffmpeg.stdout.read(1024)

            if not data:
                print("[SYSTEM] Stream ended")
                break

            yield data

        except Exception as e:
            print(f"[ERROR] {e}")
            break

    print("[SYSTEM] Cleaning up processes")

    try:
        ytdlp.kill()
    except:
        pass

    try:
        ffmpeg.kill()
    except:
        pass


@app.route("/")
def home():

    html = """
    <html>
    <head>
        <title>YouTube Audio Streams</title>
    </head>
    <body style="background:#111;color:white;font-family:Arial;padding:20px;">

        <h1>YouTube Audio Streams</h1>
        <ul>
    """

    for name in YOUTUBE_STREAMS:
        html += f'<li><a style="color:#00ccff;" href="/{name}">{name}</a></li>'

    html += """
        </ul>

    </body>
    </html>
    """

    return html


@app.route("/<channel>")
def stream(channel):

    print(f"[SYSTEM] Incoming request: {channel}")

    url = YOUTUBE_STREAMS.get(channel)

    if not url:
        print("[ERROR] Channel not found")
        return "Channel not found", 404

    print(f"[SYSTEM] Streaming URL: {url}")

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )


if __name__ == "__main__":

    print("[SYSTEM] Server starting on port 8000")

    app.run(
        host="0.0.0.0",
        port=8000,
        threaded=True
    )
