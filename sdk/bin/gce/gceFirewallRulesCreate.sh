#!/bin/bash
check_usage() {
  if [ $# -lt 8 ];
  then
    echo "Usage:"
    echo "$0 <Firewall_Rule_Name>"
    exit 1
  fi
}
check_usage $*
#gcloud computefirewall-rules create default-allow-http --direction=INGRESS --priority=1000 --network=default --action=ALLOW --rules=tcp:80 --source-ranges=0.0.0.0/0 --target-tags=http-server
gcloud compute --project=qwiklabs-gcp-44cf2aac0a91c402 firewall-rules create default-allow-http --direction=INGRESS --priority=1000 --network=default --action=ALLOW --rules=tcp:80 --source-ranges=0.0.0.0/0 --target-tags=http-server
