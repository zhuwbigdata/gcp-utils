#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <KEY_FILE_PATH>"
    exit 1
  fi
}
check_usage $*
gcloud auth activate-service-account --key-file $1 
