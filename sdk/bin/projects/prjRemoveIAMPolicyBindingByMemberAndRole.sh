#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID> <MEMBER> <ROLE>"
    exit 1
  fi
}
check_usage $*
gcloud projects remove-iam-policy-binding $1 --member=$2 --role=$3
