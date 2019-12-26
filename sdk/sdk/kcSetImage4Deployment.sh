#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <IMAGE_VERSION>"
    echo "kubectl set image deployment.v1.apps/nginx-deployment nginx=nginx:1.9.1 --record"
    exit 1
  fi
}
check_usage $*
kubectl set image deployment.v1.apps/$1 $2 --record
