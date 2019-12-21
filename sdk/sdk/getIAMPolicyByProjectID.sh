#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID>"
    exit 1
  fi
}
check_usage $*
gcloud projects get-iam-policy  $1
