#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <NETWORK_NAME> <BGP-Routing-Mode:regional|global"
    exit 1
  fi
}
check_usage $*
gcloud compute networks create  $1 \
    --subnet-mode=custom \
    --bgp-routing-mode=$2
