#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <CLUSTER_NAME> <REGION_NAME>"
    echo "Saved to ~/.kube/config"
    exit 1
  fi
}
check_usage $*
gcloud container clusters get-credentials $1 --region $2
