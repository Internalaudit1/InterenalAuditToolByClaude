FROM node:20-bookworm-slim AS web-builder

WORKDIR /app

COPY package.json package-lock.json /app/
COPY apps/web/package.json /app/apps/web/package.json
RUN npm ci

COPY apps/web /app/apps/web

ARG NEXT_PUBLIC_API_URL=/api/v1
ARG NEXT_PUBLIC_APP_NAME=HCL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME

RUN npm run build --workspace apps/web


FROM python:3.11-slim AS api-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

RUN python -m venv "$VIRTUAL_ENV"

COPY apps/api /build/apps/api
RUN pip install --upgrade pip setuptools wheel && pip install /build/apps/api


FROM node:20-bookworm-slim AS node-runtime


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/bin:$PATH"

WORKDIR /app

COPY --from=node-runtime /usr/local /usr/local
COPY --from=api-builder /opt/venv /opt/venv

COPY package.json package-lock.json /app/
COPY apps/web/package.json /app/apps/web/package.json
COPY --from=web-builder /app/node_modules /app/node_modules
COPY apps/web /app/apps/web
COPY --from=web-builder /app/apps/web/.next /app/apps/web/.next
RUN if [ -d /app/apps/web/.next/standalone/apps/web ]; then \
      mkdir -p /app/apps/web/.next/standalone/apps/web/.next && \
      cp -R /app/apps/web/public /app/apps/web/.next/standalone/apps/web/public && \
      cp -R /app/apps/web/.next/static /app/apps/web/.next/standalone/apps/web/.next/static; \
    fi

COPY apps/api /app/apps/api
COPY storage/documents /app/storage/documents
COPY storage/uploads /app/storage/uploads
COPY docker/app/proxy.mjs /app/proxy.mjs
COPY docker/app/start.sh /usr/local/bin/start-dia.sh

RUN chmod +x /usr/local/bin/start-dia.sh \
    && mkdir -p /app/storage/documents /app/storage/uploads

EXPOSE 3000

CMD ["/usr/local/bin/start-dia.sh"]
