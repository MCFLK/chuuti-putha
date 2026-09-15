FROM python:3.11-slim

# Install FFmpeg (required for audio streaming)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

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
