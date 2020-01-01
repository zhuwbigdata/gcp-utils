#!/bin/bash
check_usage() {
  if [ $# -lt 4 ]
  then
    echo "Usage:"
    echo "$0 <Instance_Template_Name> <Machine_TYPE|n1-standard-1> <IMAGE_PROJECT> <IMAGE_FAMILY>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-templates create $1  --machine-type=$2 --image-project=$3  --image-family=$4
