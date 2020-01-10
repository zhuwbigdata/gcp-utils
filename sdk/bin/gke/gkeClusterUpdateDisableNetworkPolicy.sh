#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud container clusters update $1 --enable-network-policy
