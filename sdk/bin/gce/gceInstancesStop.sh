#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances stop $1 --zone=$2
