#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> "
    exit 1
  fi
}
check_usage $*
gcloud compute instances delete $1
