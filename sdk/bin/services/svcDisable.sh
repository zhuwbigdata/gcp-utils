#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <API>"
    exit 1
  fi
}
check_usage $*
gcloud services disable  $1 --force
