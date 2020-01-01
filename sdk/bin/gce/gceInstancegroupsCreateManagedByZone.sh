#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Group_Name> <Size< <Template> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed create $1 --size=$2 --template=$3 --zone=$4
