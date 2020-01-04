#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <BUCKET_FILE_PATH>"
    exit 1
  fi
}
check_usage $*
gsutil rewrite -k $1
