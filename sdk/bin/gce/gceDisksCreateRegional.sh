#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name> <Size> <Type:pd-standard|pd-ssd> <Region>"
    exit 1
  fi
}
check_usage $*
gcloud compute disks create $1 --size=$2 --type=$3 --region=$4 
