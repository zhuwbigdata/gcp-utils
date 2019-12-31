#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <ZONE_NAME> <DNS_NAME> <DESCRIPTION> <NETWORK>"
    exit 1
  fi
}
check_usage $*
gcloud dns managed-zones create $1 \
    --dns-name=$2 \
    --description=$3 \
    --visibility=private \
    --networks=$4
