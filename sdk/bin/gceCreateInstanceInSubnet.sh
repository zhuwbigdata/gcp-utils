#!/bin/bash
check_usage() {
  if [ $# -lt 5 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <Machine_type> <Zone> <Image> <Subnet_Name"
    exit 1
  fi
}
check_usage $*
gcloud compute instances create $1 --machine-type=$2 --zone=$3 --image=$4 --subnet=$5
