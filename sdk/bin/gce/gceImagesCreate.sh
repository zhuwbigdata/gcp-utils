#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name> <Source_Disk> <Source_Disk_Zone> <Storage_Location>"
    exit 1
  fi
}
check_usage $*
gcloud compute images create $1  --source-disk=$2 --source-disk-zone=$3 --storage-location=$4
