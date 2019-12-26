#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME> <NUMBER_NODE> <ZONE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud container clusters create $1 --num-nodes S2 --zone $3 --enable-ip-alias
