#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PROPERTY_KEY> <PROPERTY_VALUE>"
    exit 1
  fi
}
check_usage $*
gcloud config set $1 $2
