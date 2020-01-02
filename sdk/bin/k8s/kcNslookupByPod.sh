#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <POD_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl exec -ti $1 -- nslookup kubernetes.default
