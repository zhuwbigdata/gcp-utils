#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <PORT_NUMBER"
    exit 1
  fi
}
check_usage $*
kubectl expose deployment $1 --target-port=$2 --type=NodePort
