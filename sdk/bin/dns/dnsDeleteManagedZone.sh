#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <ZONE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud dns managed-zones delete $1 
