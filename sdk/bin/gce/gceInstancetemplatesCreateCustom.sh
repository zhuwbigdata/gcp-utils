#!/bin/bash
check_usage() {
  if [ $# -lt 4 ]
  then
    echo "Usage:"
    echo "$0 <Instance_Template_Name> <Custom_VM_TYPE|n1> <Custom_CPU> <Custom_MEMORY:GB>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-templates create $1  --custom-vm-type=$2 --custom-cpu=$3 --custom-memory=$4 
