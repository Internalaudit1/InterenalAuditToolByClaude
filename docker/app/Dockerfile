FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    postgresql-client \
    ca-certificates \
    && python3 -m venv "$VIRTUAL_ENV" \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json /app/
COPY apps/web/package.json /app/apps/web/package.json
RUN npm ci

COPY apps/api /app/apps/api
RUN pip install --upgrade pip setuptools wheel && pip install /app/apps/api

ARG NEXT_PUBLIC_API_URL=/api/v1
ARG NEXT_PUBLIC_APP_NAME="Digital Internal Audit"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME

COPY apps/web /app/apps/web
RUN npm run build --workspace apps/web

COPY storage/uploads /app/storage/uploads
COPY docker/app/nginx.conf /etc/nginx/conf.d/dia.conf
COPY docker/app/supervisord.conf /etc/supervisor/conf.d/dia.conf
COPY docker/app/start.sh /usr/local/bin/start-dia.sh

RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf \
    && chmod +x /usr/local/bin/start-dia.sh \
    && mkdir -p /var/log/supervisor /run/nginx /app/storage/uploads

EXPOSE 3000

CMD ["/usr/local/bin/start-dia.sh"]
