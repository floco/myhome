# Stage 1: build Svelte frontend
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
COPY packages/geometry/package.json ./packages/geometry/
COPY packages/editor/package.json ./packages/editor/
RUN npm ci --ignore-scripts
COPY packages/geometry ./packages/geometry
COPY packages/editor ./packages/editor
RUN npm run -w @myhome/editor build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app
COPY packages/backend/pyproject.toml ./
RUN pip install --no-cache-dir .
COPY packages/backend/src ./src
COPY --from=frontend-build /build/packages/editor/dist ./static
EXPOSE 8000
CMD ["uvicorn", "myhome.main:app", "--host", "0.0.0.0", "--port", "8000"]
