#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <CONFIGMAP_NAME>"
    exit 1
  fi
}
check_usage $*
kubectl describe configmap $1
