#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <ROLE> <PROJECT_ID>"
    exit 1
  fi
}
check_usage $*
gcloud iam roles describe $1 --project=$2
