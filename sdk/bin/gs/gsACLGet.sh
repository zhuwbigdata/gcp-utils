#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <BUCKET_NAMED>"
    exit 1
  fi
}
check_usage $*
gsutil acl get $1
