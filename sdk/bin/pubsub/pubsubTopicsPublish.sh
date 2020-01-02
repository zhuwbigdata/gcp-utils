#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Topic> <Message>"
    exit 1
  fi
}
check_usage $*
gcloud pubsub topics publish $1  --message $2
