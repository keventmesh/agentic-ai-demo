
## Running on Kubernetes

Install pre-requisites:
- Skaffold: https://skaffold.dev/docs/install/
- Knative Eventing: https://knative.dev/docs/install/ OR using [install-100-knative-eventing.sh](hack/install-100-knative-eventing.sh)
- Strimzi: https://strimzi.io/ OR using [install-200-strimzi.sh](hack/install-200-strimzi.sh)
- Knative Eventing Kafka Broker: https://knative.dev/docs/eventing/brokers/broker-types/kafka-broker/ OR using [install-300-kn-kafka-broker.sh](hack/install-300-kn-kafka-broker.sh)

Copy the `.env.example` file to `.env` and fill in the required values.

Then for building and pushing the images, run:

```shell
make build
```

To deploy the services to your Kubernetes cluster, run:

```shell
make deploy
```

For sanity check, send a request to the intake service:

```shell
# start Kubectl port-forward to access the service
kubectl port-forward -n keventmesh svc/svc-intake 8080:80
# then, in a new terminal, send a request to the intake service:
curl -X POST http://localhost:8080/ \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com."
    }
  '
```

You should receive a response like this:

```json
{"eventId":"9b78c13a-9c38-42c7-84fa-615f45add5af","status":"event accepted"}
```

You can watch the events being processed by the services using the `ui_observer` service:

```shell
kubectl port-forward -n keventmesh svc/ui-observer 9999:80
# Then open your browser to http://localhost:9999
```

Clean up the resources:

```shell
make clean
```

## Development setup

Setup Python environment in your local machine:

```shell
pyenv install 3.11.9
pyenv local 3.11.9
$(pyenv which python) -m venv venv
source venv/bin/activate
pip install --no-cache-dir .
```

Each service has its own README file with instructions on how to run it locally.

TODO: Postgres, ChromaDB, Ollama
