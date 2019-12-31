#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <PROPERTY_KEY> <PROPERTY_VALUE>"
    exit 1
  fi
}
check_usage $*
gcloud config unset $1
