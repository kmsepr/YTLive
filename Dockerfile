FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y ffmpeg

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD gunicorn -w 1 -b 0.0.0.0:$PORT app:app
