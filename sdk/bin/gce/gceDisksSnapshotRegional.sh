#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name> <Region>"
    exit 1
  fi
}
check_usage $*
gcloud compute disks snapshot $1 --region=$2
