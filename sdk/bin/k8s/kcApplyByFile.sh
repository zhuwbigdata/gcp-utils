#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <FILE_PATH>"
    echo "This is in_place update, not disruptive update - declarative"
    exit 1
  fi
}
check_usage $*
kubectl apply -f $1
