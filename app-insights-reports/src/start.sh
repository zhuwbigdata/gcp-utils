#!/usr/bin/env bash

set -e

cd $(dirname "$BASH_SOURCE")

mkdir -p logs
export PATH=../python3/bin:$PATH
export PYTHONPATH=deps:pylib
export PYTHONPATH=$PYTHONPATH:deps
BIND=$(python -c 'import config; print(f"{config.listen_host}:{config.listen_port}")')
PID=gunicorn.pid
if [ -f $PID ]; then echo "app-insights-report is already running, use stop.sh to kill it."; exit 0; fi
python -m gunicorn main:server --daemon --pid=$PID --bind $BIND --threads=16 -w 1 --log-level debug --error-logfile logs/gunicorn_error.log --access-logfile logs/gunicorn_access.log --capture-output
echo "app-insights-reports started successfully"
