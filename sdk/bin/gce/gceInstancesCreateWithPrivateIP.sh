#!/bin/bash
check_usage() {
  if [ $# -lt 7 ];
  then
    echo "Usage:"
    echo "$0 <Instance_Name> <NETWORK> <Machine_type> <Image_Project> <Image_Family> <Subnet_Name> <Zone>"
    exit 1
  fi
}
check_usage $*
gcloud compute instances create $1 \
    --network=$2 --machine-type=$3 \
    --image-family=$5 --image-project=$4 \
    --subnet=$6 --zone=$7 \
    --private-network-ip=$8 \
    --no-address 
