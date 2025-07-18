
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
# skaffold render --default-repo="${IMAGE_REGISTRY}" --tag="${IMAGE_TAG}" | kubectl apply -f -
```

Send a request to the intake service:

```shell
# start Kubectl port-forward to access the service
kubectl port-forward -n keventmesh svc/svc-intake 8080:80
# then, in a new terminal, send a request to the intake service:
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, I need help with my password. \n Jane Doe \n"
    }
  '
```

You should receive a response like this:

```json
{"eventId":"9b78c13a-9c38-42c7-84fa-615f45add5af","status":"event accepted"}
```

Clean up the resources:

```shell
skaffold delete
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
pip install --no-cache-dir .
```

## How to run locally

Each service has its own README file with instructions on how to run it locally.

TODO: Postgres, ChromaDB, Ollama
