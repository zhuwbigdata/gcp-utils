#!/usr/bin/env bash

cd $(dirname "$BASH_SOURCE")

if [ -f gunicorn.pid ]; then
    kill -SIGINT $(cat gunicorn.pid)
    rm gunicorn.pid
    echo "app-insights-reports stopped successfully"
    exit 0
fi
