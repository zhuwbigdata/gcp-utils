#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <FILE_PATH>"
    echo "This is disruptive update, not in-place update - declarative"
    exit 1
  fi
}
check_usage $*
kubectl replace -f $1
