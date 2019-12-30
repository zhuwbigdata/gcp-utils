#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name> <Size> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute disks create $1 --size=$2 --zone=$3 
