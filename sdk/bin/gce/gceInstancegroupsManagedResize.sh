#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <MIG_NAME> <SIZE>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed resize $1 --size=$2
