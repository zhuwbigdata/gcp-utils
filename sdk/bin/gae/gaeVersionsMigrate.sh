#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <VERSION_NAME> <SERVICE_NAME> "
    exit 1
  fi
}
check_usage $*
gcloud app versions migrate  $1 --service=$2
