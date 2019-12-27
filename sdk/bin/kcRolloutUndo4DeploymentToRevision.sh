#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <REVISION_NUMBER>"
    exit 1
  fi
}
check_usage $*
kubectl rollout undo deployments $1 --to-revision=$2
