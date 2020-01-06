#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Health_Check_Name>"
    exit 1
  fi
}
check_usage $*
gcloud compute health-checks  describe $1  
