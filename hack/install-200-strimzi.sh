#!/usr/bin/env bash

set -e
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"/library.sh

strimzi_version='0.45.1'

header "Using Strimzi Version:                  ${strimzi_version}"

header "Strimzi install"
kubectl create namespace kafka || true
kubectl -n kafka apply --selector strimzi.io/crd-install=true -f https://github.com/strimzi/strimzi-kafka-operator/releases/download/${strimzi_version}/strimzi-cluster-operator-${strimzi_version}.yaml
curl -L "https://github.com/strimzi/strimzi-kafka-operator/releases/download/${strimzi_version}/strimzi-cluster-operator-${strimzi_version}.yaml" \
  | sed 's/namespace: .*/namespace: kafka/' \
  | kubectl -n kafka apply -f -

# Wait for the CRD we need to actually be active
kubectl wait crd --timeout=-1s kafkas.kafka.strimzi.io --for=condition=Established

header "Applying Strimzi Cluster file"
kubectl -n kafka apply -f "https://raw.githubusercontent.com/strimzi/strimzi-kafka-operator/${strimzi_version}/examples/kafka/kafka-persistent-single.yaml"
header "Waiting for Strimzi to become ready"
kubectl wait kafka --all --timeout=-1s --for=condition=Ready -n kafka
