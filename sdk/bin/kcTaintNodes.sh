#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <NODE_NAME> <key> <value> <EFFECT:NoSchedule,NoExecute>"
    exit 1
  fi
}
check_usage $*
kubectl taint nodes $1 $2=$3:$4
