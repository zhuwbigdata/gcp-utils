#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Group_Name> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed describe $1 --zone=$2
