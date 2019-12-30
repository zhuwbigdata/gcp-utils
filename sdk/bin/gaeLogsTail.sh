#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <SERVICE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud app logs tail -s $1 
