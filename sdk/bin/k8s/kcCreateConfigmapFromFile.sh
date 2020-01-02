#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <CONFIGMAP_NAME> <CONFIG_FILE_PATH>"
    exit 1
  fi
}
check_usage $*
kubectl  create configmap $1 --from-file=$2
