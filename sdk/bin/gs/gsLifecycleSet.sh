#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <LC_JSON> <BUCKET_NAMED>"
    exit 1
  fi
}
check_usage $*
gsutil lifecycle set  $1 $2
