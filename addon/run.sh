#!/bin/sh
cd /app
exec uvicorn myhome.main:app --host 0.0.0.0 --port 8000
