#!/usr/bin/env bash

set -e
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")"/library.sh

eventing_kafka_broker_version="v1.17.3"
eventing_kafka_broker_url=https://github.com/knative-sandbox/eventing-kafka-broker/releases/download/knative-${eventing_kafka_broker_version}

header "Using Knative Kafka Broker Version:         ${eventing_kafka_broker_version}"

header "Setting up Knative Eventing Kafka suite "
curl -L ${eventing_kafka_broker_url}/eventing-kafka.yaml \
  | sed 's/namespace: .*/namespace: knative-eventing/' \
  | sed 's/default.topic.replication.factor: .*/default.topic.replication.factor: "1"/' \
  | sed 's/REPLACE_WITH_CLUSTER_URL/my-cluster-kafka-bootstrap.kafka:9092/' \
  | kubectl apply -f - -n knative-eventing

header "Waiting for Knative Apache Kafka suite to become ready"
kubectl wait deployment --all --timeout=-1s --for=condition=Available -n knative-eventing
