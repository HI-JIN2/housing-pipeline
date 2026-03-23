# Production Dockerfile for Admin Agent
FROM python:3.9-slim

WORKDIR /app

# Install dependencies first for caching
COPY admin-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy agent code
COPY admin-agent /app/admin-agent

# Set python path to include the root for shared module access
ENV PYTHONPATH=/app:/app/admin-agent

EXPOSE 8002

CMD ["uvicorn", "admin-agent.main:app", "--host", "0.0.0.0", "--port", "8002"]
