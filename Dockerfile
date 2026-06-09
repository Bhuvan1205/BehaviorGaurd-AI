FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install system dependencies for build-essential (in case any packages require compiling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt psycopg2-binary python-dotenv

# Copy required application files and directories
COPY app/ ./app/
COPY notebooks/models/ ./notebooks/models/
COPY notebooks/artifacts/ ./notebooks/artifacts/
COPY Database/ ./Database/
COPY setup_db.py .
COPY seed_demo_data.py .
COPY entrypoint.sh .

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Run the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
