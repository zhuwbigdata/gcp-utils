#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <REPLICAS>"
    exit 1
  fi
}
check_usage $*
kubectl scale  deployment $1 --replicas=$2
