#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <LIST OF YAML files>"
    exit 1
  fi
}
check_usage $*
gcloud app deploy $@
