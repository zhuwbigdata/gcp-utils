#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Forwarding_rule_name> <Region>"
    exit 1
  fi
}
check_usage $*
gcloud compute forwarding-rules  describe $1 --region=$2 
