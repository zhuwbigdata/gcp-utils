#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAM> <ZONE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud container clusters describe $1 --zone=$2
