#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <EXTERNAL_IP_NAME> <REGION>"
    exit 1
  fi
}
check_usage $*
gcloud compute addresses describe $1  --region=$2
