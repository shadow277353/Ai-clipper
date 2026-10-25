FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data/uploads /data/clips
ENV DATA_DIR=/data
EXPOSE 10000
CMD ["sh","-c","gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 3600 app:app"]
