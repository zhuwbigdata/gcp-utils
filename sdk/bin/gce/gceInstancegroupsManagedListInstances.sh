#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <MIG_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed list-instances $1 
