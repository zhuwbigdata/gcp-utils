#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <REGION>"
    exit 1
  fi
}
check_usage $*
gcloud compute regions describe $1
