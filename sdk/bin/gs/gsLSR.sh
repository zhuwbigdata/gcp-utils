#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <BUCKET_URL>"
    exit 1
  fi
}
check_usage $*
gsutil ls -r  $1 
