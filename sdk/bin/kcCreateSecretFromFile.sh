#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <SECRET_NAME> <SECRET_FILE_PATH>"
    exit 1
  fi
}
check_usage $*
kubectl  create secret generic $1 --from-file=$2
