FROM python:3.11.4-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11.4-slim

WORKDIR /app

# Copy only necessary application files
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/
COPY run.sh .
RUN chmod +x run.sh

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

CMD ["./run.sh"]
