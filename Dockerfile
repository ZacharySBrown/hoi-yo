FROM python:3.11-slim

LABEL maintainer="hoi-yo"
LABEL description="Local testing image for hoi-yo orchestrator + dashboard (no HOI4)"

WORKDIR /app

# Install system deps for websockets / uvicorn
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY personas/ personas/
COPY config.toml .

# Install the project
RUN pip install --no-cache-dir .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

CMD ["hoi-yo", "run", "--local"]
