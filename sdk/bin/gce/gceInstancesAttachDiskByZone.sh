#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <DISK_NAME> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances attach-disk $1 --disk $2 --zone $3
