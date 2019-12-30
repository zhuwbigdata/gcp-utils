#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <REGION_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud app create --region $1
