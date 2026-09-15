FROM python:3.11-slim

# Install system dependencies (FFmpeg for audio, curl/unzip for Deno)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno (Required by yt-dlp to decrypt YouTube streams)
ENV DENO_INSTALL="/root/.deno"
ENV PATH="$DENO_INSTALL/bin:$PATH"
RUN curl -fsSL https://deno.land/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 8000 for Koyeb health check
EXPOSE 8000

# Run the bot
CMD ["python", "main.py"]
