
## Running on Kubernetes

Install pre-requisites:
- Skaffold: https://skaffold.dev/docs/install/
- Knative Eventing: https://knative.dev/docs/install/ OR using [install-100-knative-eventing.sh](hack/install-100-knative-eventing.sh)
- Strimzi: https://strimzi.io/ OR using [install-200-strimzi.sh](hack/install-200-strimzi.sh)
- Knative Eventing Kafka Broker: https://knative.dev/docs/eventing/brokers/broker-types/kafka-broker/ OR using [install-300-kn-kafka-broker.sh](hack/install-300-kn-kafka-broker.sh)

Set up some environment variables in your shell:

```shell
export IMAGE_REGISTRY="docker.io/aliok"
export IMAGE_TAG="latest"
```

Build the images:
```shell
skaffold build --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}"
```

Run the application on Kubernetes:

```shell
skaffold run --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}"
# on Minikube/kind, you can use:
# skaffold deploy --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}" --load-images=true
# or, 2 steps:
# skaffold build --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}" | kubectl apply -f -
```

## Building and pushing images

```shell
skaffold build --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}" --push
```


## Setup Python Environment
```shell
pyenv install 3.11.9
pyenv local 3.11.9
$(pyenv which python) -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## How to run locally

Each service has its own README file with instructions on how to run it locally.

TODO: Postgres, ChromaDB, Ollama
