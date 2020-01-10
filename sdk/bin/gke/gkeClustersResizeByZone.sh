#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME> <NODE_POOL> <NUMBER_NODE> <ZONE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud container clusters resize $1 --node-pool=$2 --size=$3 --zone=$4
