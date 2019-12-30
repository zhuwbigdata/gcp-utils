#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <SECRET_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl get secret $1 -o yaml 
