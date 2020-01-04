#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PERMISION, e.g. AllUers:R> <BUCKET_FILE>"
    exit 1
  fi
}
check_usage $*
gsutil acl ch -u $1 $2
