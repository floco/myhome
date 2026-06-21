#!/usr/bin/env bash
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${DATA_DIR:-/tmp/myhome-dev}"

mkdir -p "$DATA_DIR"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
}
trap cleanup INT TERM

echo "Starting backend on http://localhost:8000 (DATA_DIR=$DATA_DIR)"
cd "$REPO/packages/backend"
DATA_DIR="$DATA_DIR" uvicorn myhome.main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173"
cd "$REPO/packages/editor"
npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

wait
