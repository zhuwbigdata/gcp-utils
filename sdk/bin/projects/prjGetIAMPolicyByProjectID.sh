#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID> <FORMAT: yaml or json>"
    exit 1
  fi
}
check_usage $*
gcloud projects get-iam-policy  $1 --format=$2
