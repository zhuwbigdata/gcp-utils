#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <STATEFULSET_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl describe statefulset $1 
