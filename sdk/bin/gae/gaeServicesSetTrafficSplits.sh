#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <SERVICE_NAME> <SPLITS_SPEC:>"
    exit 1
  fi
}
check_usage $*
gcloud app services set-traffic $1 --splits $2
