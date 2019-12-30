#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <SECRET_NAME> <SECRET_KEY> <SECRET_VALUE>"
    exit 1
  fi
}
check_usage $*
kubectl  create secret generic $1 --from-literal=$2=$3
