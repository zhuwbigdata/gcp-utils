#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <ACCOUNT_ID>"
    exit 1
  fi
}
check_usage $*
gcloud beta billing accounts get-iam-policy $1
