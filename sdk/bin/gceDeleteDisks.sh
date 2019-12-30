#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Disk_Name>"
    exit 1
  fi
}
check_usage $*
gcloud compute disks delete $1 
