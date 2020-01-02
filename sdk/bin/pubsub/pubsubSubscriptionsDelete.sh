#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Subscription_Name>"
    exit 1
  fi
}
check_usage $*
gcloud pubsub subscriptions delete $1 
