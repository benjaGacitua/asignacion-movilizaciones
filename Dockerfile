FROM python:3.12-slim

ARG SUPERCRONIC_VERSION=v0.2.33
ARG SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLo /usr/local/bin/supercronic "$SUPERCRONIC_URL" \
    && chmod +x /usr/local/bin/supercronic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs \
    && printf '0 8 * * * cd /app && /usr/local/bin/python -m src.main >> /app/logs/movilizaciones.log 2>&1\n' > /app/crontab

CMD ["supercronic", "/app/crontab"]
