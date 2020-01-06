#!/bin/bash
check_usage() {
  if [ $# -lt 4 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Group_Name> <Size< <Template> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instance-groups managed create $1 --size=$2 --template=$3 --zone=$4
#gcloud beta compute --project=qwiklabs-gcp-d2fc91349ffaa19a instance-groups managed create europe-west1-mig --base-instance-name=europe-west1-mig --template=mywebserver-template --size=1 --zones=europe-west1-b,europe-west1-c,europe-west1-d --instance-redistribution-type=PROACTIVE --health-check=http-health-check --initial-delay=60

#gcloud beta compute --project "qwiklabs-gcp-d2fc91349ffaa19a" instance-groups managed set-autoscaling "europe-west1-mig" --region "europe-west1" --cool-down-period "60" --max-num-replicas "5" --min-num-replicas "1" --target-cpu-utilization "0.6"
