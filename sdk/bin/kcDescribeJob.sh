#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <JOB_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl describe job $1 
