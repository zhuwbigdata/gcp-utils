#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <FILE_PATH>"
    exit 1
  fi
}
check_usage $*
kubectl apply -f $1
