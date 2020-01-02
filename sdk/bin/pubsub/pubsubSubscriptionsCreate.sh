#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Topic> <Subscription_Name>"
    exit 1
  fi
}
check_usage $*
gcloud pubsub subscriptions create --topic $1 $2 
