FROM python:3.11-slim

# Install system dependencies including FFmpeg and Opus for audio/voice
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libffi-dev \
    libsodium-dev \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire application
COPY . .

# Ensure executable permissions on startup script
RUN chmod +x start_cloud.sh

# Expose web server port
EXPOSE 5000

# Run unified 24/7 cloud startup script (runs both Bot & Training Suite)
CMD ["./start_cloud.sh"]
