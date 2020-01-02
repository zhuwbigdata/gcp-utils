#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl delete deployment $1
