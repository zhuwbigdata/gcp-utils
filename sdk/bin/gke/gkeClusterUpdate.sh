#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME> <Flag>"
    gcloud container clusters update --help
    exit 1
  fi
}
check_usage $*
gcloud container clusters update $1 $2 
