#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <EXTERNAL_IP_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud compute addresses describe $1  --global
