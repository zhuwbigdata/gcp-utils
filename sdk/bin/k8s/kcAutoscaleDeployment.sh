#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <DEPLOYMENT_NAME> <MAX> <MIN> <CPU_PERCENT>""
    exit 1
  fi
}
check_usage $*
kubectl autoscale deployment $1 --max $2--min $3 --cpu-percent $4 
