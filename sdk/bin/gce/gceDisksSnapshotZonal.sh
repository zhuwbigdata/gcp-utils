#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name> <Storage_Location>"
    exit 1
  fi
}
check_usage $*
gcloud compute disks snapshot=$1 --storage-location=$2
