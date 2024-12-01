#!/usr/bin/env sh

set -e
cd /application
alembic upgrade head
pip install pydantic[dotenv]
cd /application/app
gunicorn main:app --bind 0.0.0.0:$APP_PORT -w 4 -k uvicorn.workers.UvicornWorker