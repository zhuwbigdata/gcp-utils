#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Firewall_Rule_Name>"
    exit 1
  fi
}
check_usage $*
gcloud compute firewall-rules describe $1 
