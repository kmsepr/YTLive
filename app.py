from flask import Flask, Response
import subprocess

app = Flask(__name__)

# YouTube Live Channels
YOUTUBE_STREAMS = {
    "media_one": "https://www.youtube.com/watch?v=-8d8-c0yvyU"
}

# FFmpeg settings
FFMPEG_CMD = [
    "ffmpeg",
    "-i", "pipe:0",
    "-vn",
    "-ac", "1",          # mono audio
    "-ar", "22050",      # sample rate
    "-b:a", "40k",       # bitrate
    "-f", "mp3",
    "-"
]


def generate_stream(url):
    """
    Get YouTube audio using yt-dlp
    and convert to MP3 using ffmpeg
    """

    ytdlp = subprocess.Popen(
        [
            "yt-dlp",
            "-f", "bestaudio",
            "-o", "-",
            "--live-from-start",
            url
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    ffmpeg = subprocess.Popen(
        FFMPEG_CMD,
        stdin=ytdlp.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    while True:
        data = ffmpeg.stdout.read(1024)

        if not data:
            break

        yield data


@app.route("/")
def home():

    html = """
    <html>
    <head>
        <title>YouTube Audio Streams</title>
        <style>
            body {
                font-family: Arial;
                background: #111;
                color: white;
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
                margin: 12px 0;
            }
        </style>
    </head>
    <body>

        <h1>Available Channels</h1>

        <ul>
    """

    for name in YOUTUBE_STREAMS:
        html += f'<li>🎧 <a href="/{name}">{name}</a></li>'

    html += """
        </ul>

    </body>
    </html>
    """

    return html


@app.route("/<channel>")
def stream(channel):

    url = YOUTUBE_STREAMS.get(channel)

    if not url:
        return "Channel not found", 404

    return Response(
        generate_stream(url),
        mimetype="audio/mpeg"
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        threaded=True
    )
