#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID> <ACCOUNT_ID>"
    exit 1
  fi
}
check_usage $*
gcloud beta billing projects link $1 --billing-account=$2
