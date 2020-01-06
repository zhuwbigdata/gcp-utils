#!/bin/bash
check_usage() {
  if [ $# -lt 2 ];
  then
    echo "Usage:"
    echo "$0 <Deployment_Name> <Template_File>""
    echo "Needs to update after preview ..."
    exit 1
  fi
}
check_usage $*
gcloud deployment-manager deployments update $1 --config=$2 
