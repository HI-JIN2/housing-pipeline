# Production Dockerfile for Geo Agent
FROM python:3.9-slim

WORKDIR /app

# Install dependencies first
COPY geo-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy agent code
COPY geo-agent /app/geo-agent

# Set python path
ENV PYTHONPATH=/app:/app/geo-agent

EXPOSE 8001

CMD ["uvicorn", "geo-agent.main:app", "--host", "0.0.0.0", "--port", "8001"]
