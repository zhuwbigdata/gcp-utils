#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <NETWORK_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud compute networks describe  $1
