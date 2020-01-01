#!/bin/bash
check_usage() {
  if [ $# -lt 6 ]
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <Custom_VM_TYPE|n1> <Custom_CPU> <Custom_MEMORY> <Zone> <Image>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances create $1  --custom-vm-type=$2 --custom-cpu=$3 --custom-memory=$4 --zone=$5 --image=$6
