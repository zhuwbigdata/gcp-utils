#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <PROJECT_ID> <POLICY_FILE_IN_JSON_OR_YAML>"
    echo "Notes: json format is fine, but not yaml"
    exit 1
  fi
}
check_usage $*
gcloud projects set-iam-policy  $1 $2
