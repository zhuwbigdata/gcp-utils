#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME> <NUMBER_NODE> <REGION_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud container clusters create $1 --num-nodes S2 --region $3 --enable-ip-alias 
