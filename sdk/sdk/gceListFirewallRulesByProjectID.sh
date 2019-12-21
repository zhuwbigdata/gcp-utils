#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID>"
    exit 1
  fi
}
check_usage $*
gcloud compute firewall-rules  list --project $1 
