#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID> <PROJECT_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud projects create $1 --name $2 
