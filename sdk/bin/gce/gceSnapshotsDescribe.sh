#!/bin/bash
check_usage() {
  if [ $# -lt 1 ];
  then
    echo "Usage:"
    echo "$0 <Snapshot_Name>"
    exit 1
  fi
}
check_usage $*
gcloud compute snapshots describe $1 
