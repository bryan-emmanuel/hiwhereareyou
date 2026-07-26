FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and default configuration
COPY src/ ./src/
COPY config/ ./config/

# Create a volume directory for pre-generated QR codes
RUN mkdir -p /app/qrs

# Set PYTHONPATH so absolute imports work correctly
ENV PYTHONPATH=/app
ENV SCAVENGER_CONFIG_PATH=/app/config/config.yml

# Default command starts the Telegram bot
CMD ["python", "src/main.py"]
