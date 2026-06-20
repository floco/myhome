# Stage 1: build Svelte frontend (always amd64 — rolldown has no arm/v6/v7 binaries)
FROM --platform=linux/amd64 node:22-alpine AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
COPY packages/geometry/package.json ./packages/geometry/
COPY packages/editor/package.json ./packages/editor/
RUN npm ci --ignore-scripts
COPY packages/geometry ./packages/geometry
COPY packages/editor ./packages/editor
RUN npm run -w @myhome/editor build

# Stage 2: Python backend + static assets
FROM python:3.12-slim
WORKDIR /app
COPY packages/backend/pyproject.toml ./
COPY packages/backend/src ./src
RUN pip install --no-cache-dir .
COPY --from=frontend-build /build/packages/editor/dist ./static
COPY addon/run.sh /run.sh
RUN chmod +x /run.sh
ENV STATIC_DIR=/app/static
EXPOSE 8000
CMD ["/run.sh"]
