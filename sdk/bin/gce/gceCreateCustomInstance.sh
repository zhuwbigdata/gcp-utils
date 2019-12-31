#!/bin/bash
check_usage() {
  if [ $# -lt 5 ]
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <Custom_CPU> <Custom_MEMORY> <Zone> <Image>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances create $1 --custom-cpu=$2 --custom-memory=$3 --zone=$4 --image=$5
