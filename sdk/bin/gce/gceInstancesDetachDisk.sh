#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <DISK_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances detach-disk $1 --disk=$2
