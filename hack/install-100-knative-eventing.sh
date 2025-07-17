#!/usr/bin/env bash

# exit on error
set -e
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"/library.sh

eventing_version="v1.18.1"
eventing_url=https://github.com/knative/eventing/releases/download/knative-${eventing_version}

while [[ $# -ne 0 ]]; do
   parameter=$1
   case ${parameter} in
     --nightly)
        nightly=1
        eventing_version=nightly
        eventing_url=https://knative-nightly.storage.googleapis.com/eventing/latest
       ;;
     *) abort "unknown option ${parameter}" ;;
   esac
   shift
 done


header "Using Knative Eventing Version:         ${eventing_version}"

header "Setting up Knative Eventing"
kubectl apply --filename $eventing_url/eventing.yaml

header "Waiting for Knative Eventing to become ready"
kubectl wait deployment --all --timeout=-1s --for=condition=Available -n knative-eventing
