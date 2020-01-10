#!/bin/bash
check_usage() {
  if [ $# -lt 3 ];
  then
    echo "Usage:"
    echo "$0 <SRC_ROLE_NAME> <DEST_ROLE_NAME> <ORGANIZATION_ID>"
    exit 1
  fi
}
check_usage $*
gcloud iam roles copy --source $1 --destination $2 --dest-organization $3 
