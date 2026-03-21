# Production Dockerfile for Parser Agent
FROM python:3.9-slim

WORKDIR /app

# Install dependencies first for caching
COPY parser-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy agent code
COPY parser-agent /app/parser-agent

# Set python path to include the root for shared module access
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "parser-agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
