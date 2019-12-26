#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <POD_NAME> <SELECTOR>"
    exit 1
  fi
}
check_usage $*
kubectl describe pod $1 --selector=$2
