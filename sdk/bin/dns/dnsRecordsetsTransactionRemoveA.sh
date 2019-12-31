#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <IP_ADDR> <DOMAIN_NAME> <TTL> <<ZONE_NAME>"
    exit 1
  fi
}
check_usage $*
gcloud dns record-sets transaction remove $1 \
      --name=$2 --ttl=$3 \
      --type=A --zone=$4
