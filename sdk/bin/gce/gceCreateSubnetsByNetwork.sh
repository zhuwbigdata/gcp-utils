#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <NETWORK_NAME> <SUBNET_NAME> <REGION> <RANGE>"
    exit 1
  fi
}
check_usage $*
gcloud compute networks subnets create $2  --network=$1 --region=$3 --range=$4
