#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <REVISION>"
    exit 1
  fi
}
check_usage $*
kubectl rollout history deployment $1 --revision=$2
