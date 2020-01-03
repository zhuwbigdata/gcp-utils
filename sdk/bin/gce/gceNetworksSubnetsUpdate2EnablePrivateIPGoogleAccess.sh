#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <SUBNET_NAME> <REGION>"
    exit 1
  fi
}
check_usage $*
gcloud compute networks subnets update $1 \
       --region=$2 --enable-private-ip-google-access
