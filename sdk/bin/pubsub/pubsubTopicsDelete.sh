#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <TOPIC>"
    exit 1
  fi
}
check_usage $*
gcloud pubsub topics delete $1
