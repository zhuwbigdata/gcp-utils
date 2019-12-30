#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <VERSION_NUMBER>"
    exit 1
  fi
}
check_usage $*
gcloud app browse -v $1
