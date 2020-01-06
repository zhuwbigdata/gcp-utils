#!/bin/bash
gcloud compute forwarding-rules list
#NAME                    REGION       IP_ADDRESS  IP_PROTOCOL  TARGET
#my-ilb-forwarding-rule  us-central1  10.10.30.5  TCP          us-central1/backendServices/my-ilb
