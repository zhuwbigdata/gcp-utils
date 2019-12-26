#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <POOL_NAME> <NUM_NODES> <CLUSTER_NAME> <ZONE_NAME> <LABEL>"
    exit 1
  fi
}
check_usage $*
gcloud container node-pools create $1 \
  --cluster=$3 --zone=$4 \
  --num-nodes $2 --node-labels=$5 
