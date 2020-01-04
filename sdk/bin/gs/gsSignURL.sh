#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <Period> <PrivateKey_Path>> <Bucket_Name>"
    exit 1
  fi
}
check_usage $*
gsutil signurl -d $1 $2 gs://$3
