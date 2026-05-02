FROM python:3.11-slim

WORKDIR /app

# Server-only deps
COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

# Game logic + config (server reuses these verbatim)
COPY config.py /app/config.py
COPY game /app/game
COPY server /app/server

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    DECLARE_HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "-m", "server.server"]
