FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/
RUN pip install --no-cache-dir -e .

# Environment settings
ENV PYTHONUNBUFFERED=1

# Universal stdio transport entrypoint
ENTRYPOINT ["python", "-u", "server.py"]
