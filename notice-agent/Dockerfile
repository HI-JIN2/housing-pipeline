FROM python:3.9-slim

WORKDIR /app

COPY notice-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY notice-agent /app/notice-agent

ENV PYTHONPATH=/app:/app/notice-agent

EXPOSE 8003

CMD ["uvicorn", "notice-agent.main:app", "--host", "0.0.0.0", "--port", "8003"]
