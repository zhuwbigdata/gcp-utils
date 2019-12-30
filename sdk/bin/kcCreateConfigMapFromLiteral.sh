#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <CONFIGMAP_NAME> <CONFIG_KEY> <CONFIG_VALUE>"
    exit 1
  fi
}
check_usage $*
kubectl  create configmap $1 --from-literal=$2=$3
