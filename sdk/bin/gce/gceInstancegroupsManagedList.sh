#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <FILTER e.g.name='my-f1-mig'>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed list --filter=$1 
