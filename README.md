## Running on Kubernetes

Install pre-requisites:
- Skaffold: https://skaffold.dev/docs/install/
- Knative Eventing: https://knative.dev/docs/install/ OR using [install-100-knative-eventing.sh](hack/install-100-knative-eventing.sh)
- Knative Serving: https://knative.dev/docs/install/ OR using [install-150-knative-serving.sh](hack/install-150-knative-serving.sh)
- Strimzi: https://strimzi.io/ OR using [install-200-strimzi.sh](hack/install-200-strimzi.sh)
- Knative Eventing Kafka Broker: https://knative.dev/docs/eventing/brokers/broker-types/kafka-broker/ OR using [install-300-kn-kafka-broker.sh](hack/install-300-kn-kafka-broker.sh)

Copy the `.env.example` file to `.env` and fill in the required values.

See [Models to use](#models-to-use) section for recommended models.
See [Using with Ollama](#using-with-ollama) section for Ollama setup.

Then for building and pushing the images, run:

```shell
make build
```

To deploy the services to your Kubernetes cluster, run:

```shell
make deploy
```

### Accessing Services from your Local Network (for Kind/Minikube)

The default sanity check below uses `kubectl port-forward`, which makes services available only on `localhost`. If you are running Kubernetes in a local cluster (like Kind or Minikube) and want to access services directly from your network, follow these steps.

#### 1. Expose the Knative Ingress Gateway

By default, the Knative ingress (Kourier) might be set up as a `LoadBalancer` service, which doesn't get an external IP on local clusters. We will patch it to use a predictable `NodePort`, making it accessible on the node's IP address.

```shell
kubectl patch service kourier \
  --namespace kourier-system \
  --type='strategic' \
  --patch='{"spec":{"type":"NodePort","ports":[{"port":80,"nodePort":31080},{"port":443,"nodePort":31443}]}}'
```

#### 2. Configure a Custom Domain for Knative

To get clean, predictable URLs like `svc-intake.keventmesh.example.com`, we need to configure Knative's default domain. This command sets `example.com` as the base domain for all services.

```shell
kubectl patch configmap/config-domain \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"example.com":""}}'
```

#### 3. Find Your Kubernetes Node's IP Address

You need the IP address of the machine hosting your Kubernetes cluster on your local network.

#### 4. Send a Request

Now you can send a request to the intake service using `curl`, the node's IP, and the NodePort (`31080`). The `-H "Host: ..."` header is crucial as it tells the ingress which Knative service to route the request to.

```shell
# Replace with the IP address you found in the previous step
export NODE_IP=192.168.2.151

# Send the request
curl -v -X POST http://${NODE_IP}:31080 \
  -H "Host: svc-intake.keventmesh.example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com."
    }
  '
```
You should receive the same `{"eventId":...}` response as the port-forward method. You can now proceed to the "Viewing the Full Event Flow" section.

### Sanity Check (Using Port-Forward)

Send a generic request to the intake service to start the event flow:

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

### Viewing the Full Event Flow

You can watch all events being processed by the services using the `ui_observer` service:

```shell
kubectl port-forward -n keventmesh svc/ui-observer 9999:80
# Then open your browser to http://localhost:9999
```

### Viewing the Finance Inbox

If your messages is a finance related one, you can see it in the finance inbox (no inboxes available currently for other message kinds):

1.  Port-forward the finance responder service:
    ```shell
    kubectl port-forward -n keventmesh svc/svc-finance-responder 8888:80
    ```

2.  Open your browser to **http://localhost:8888**.

3.  In a separate terminal, send a new, finance-related message to the intake service. You can use either the `port-forward` method on `localhost:8080` or the network method from the section above:
    ```shell
    # Using the network method (replace NODE_IP)
    curl -X POST http://${NODE_IP}:31080 \
      -H "Host: svc-intake.keventmesh.example.com" \
      -H "Content-Type: application/json" \
      -d '{
        "content": "Hi, I need to dispute a charge on my last invoice, #INV-2025-07. I believe I was overcharged for the premium subscription tier. Can you please look into this and issue a refund? My account email is john.smith@globaltech.com. Thanks, John."
        }
      '
    ```
    You will see the message appear in the Finance Inbox in your browser in real-time.

### Clean up

Clean up the resources:

```shell
make clean
```

## Using with Ollama

To use models via Ollama, you need the Kubernetes cluster to have access to the Ollama server.

By default, Ollama will only listen localhost. You can make it listen on an external IP:

```shell
OLLAMA_HOST=1.2.3.4:11434 ollama serve
```

Then, adjust your `.env` file to point to the Ollama server (`/v1` at the end is important):

```env
STRUCTURE_PROCESSOR_API_BASE_URL=https://1.2.3.4:11434/v1
...
```

## Models to use

| Env Variable                   | Description                                                                            | Recommended Model         | Recommended Ollama Model |
|--------------------------------|----------------------------------------------------------------------------------------|---------------------------|--------------------------|
| STRUCTURE_PROCESSOR_MODEL_NAME | A model to process the structure of the text and fill in JSON. Should support tooling. | `granite-3-3-8b-instruct` | `granite3.3:8b`          |
| GUARDIAN_PROCESSOR_MODEL_NAME  | A guardian model to evaluate the content of the text and return Yes/No output.         | `granite3-guardian-2b`    | `granite3-guardian:2b`   |
| ROUTER_MODEL_NAME              | A model to categorize the message.                                                     | `granite-3-3-8b-instruct` | `granite3.3:8b`          |


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
