# AI-Powered Event-Driven Triage System

This project demonstrates an event-driven architecture for triaging and processing incoming messages using Knative, Kafka, and Large Language Models (LLMs). The system is designed to run on any Kubernetes cluster and includes specific instructions for deploying on OpenShift.

## High-Level Architecture

1.  **Intake:** An `svc-intake` service accepts raw text messages via a REST API.
2.  **Eventing Backbone:** It publishes the message as a CloudEvent to a Knative Kafka Broker.
3.  **Processing Pipeline:** A series of services subscribe to events from the broker to perform specific tasks in sequence:
    *   `svc-structure-processor`: Uses an LLM to extract structured data (e.g., name, email, reason) from the message.
    *   `svc-guardian-processor`: Uses an LLM to check the message for harmful content.
    *   `svc-customer-lookup`: Enriches the event with customer information from a PostgreSQL database.
    *   `svc-router`: Uses an LLM to classify the message and route it to the appropriate department (e.g., Finance, Support).
4.  **Responders & UIs:**
    *   `svc-finance-responder`: A simple web UI that acts as a real-time inbox for messages routed to the finance team.
    *   `ui-observer`: A real-time dashboard that visualizes the entire journey of every event through the system.

## Running on Kubernetes

### 1. Prerequisites

- Skaffold: https://skaffold.dev/docs/install/
- Knative Eventing: https://knative.dev/docs/install/ OR using [install-100-knative-eventing.sh](hack/install-100-knative-eventing.sh)
- Knative Serving: https://knative.dev/docs/install/ OR using [install-150-knative-serving.sh](hack/install-150-knative-serving.sh)
- Strimzi: https://strimzi.io/ OR using [install-200-strimzi.sh](hack/install-200-strimzi.sh)
- Knative Kafka Broker: https://knative.dev/docs/eventing/brokers/broker-types/kafka-broker/ OR using [install-300-kn-kafka-broker.sh](hack/install-300-kn-kafka-broker.sh)

### 2. Configuration

Copy the `.env.example` file to `.env` and fill in the required values for your image registry and LLM endpoints.
```shell
cp .env.example .env
# Edit .env with your details
```

See [Models to use](#models-to-use) section for recommended models.
See [Using with Ollama](#using-with-ollama) section for Ollama setup.

### 3. Build and Deploy

First, build the container images and push them to your public registry.
```shell
make build
```

Next, deploy all the services and resources to your Kubernetes cluster.
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

#### Viewing the Live Dashboards

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

To remove all deployed resources, run:
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

## Running on OpenShift

This guide explains how to deploy the application on an OpenShift cluster using a local build and push workflow.

### 1. Prerequisites

- **OpenShift CLI (`oc`):** [Install the OpenShift CLI](https://docs.openshift.com/container-platform/latest/cli_reference/openshift_cli/installing-cli.html).
- **Log in to your cluster:** Use `oc login ...` to connect to your OpenShift cluster. You will need permissions to create a new project.
- **Operators:** From the OpenShift Console, an administrator must install the following operators from **OperatorHub**:
    - **OpenShift Serverless:** This provides Knative Serving and Eventing.
    - **Red Hat AMQ Streams:** This provides a supported Strimzi/Kafka distribution.
- After installing the operators, ensure that instances of `KnativeServing`, `KnativeEventing`, `KnativeKafka` and a `Kafka` cluster are running.

### 2. OpenShift-Specific Configuration

Copy the `.env.example` file to `.env` and fill in the required values:
-   `IMAGE_REGISTRY`: Your Docker Hub username (e.g., `docker.io/your_docker_username`).
-   LLM API keys and URLs as needed.

### 3. Build and Push Images

From your local machine, build the container images and push them to your public registry. The updated `Dockerfile` is compatible with OpenShift's security requirements.
```shell
make build
```
This will build all service images and push them to the registry specified in your `.env` file.

### 4. Deploy to OpenShift

First, create the project (namespace) for the application:
```shell
oc new-project keventmesh
```

The official PostgreSQL container image requires specific permissions to run on OpenShift. Grant the `anyuid` Security Context Constraint (SCC) to the default service account in your project. This allows the database pod to run with its required internal user ID.
```shell
oc adm policy add-scc-to-user anyuid -z default -n keventmesh
```

Now, deploy the application using the OpenShift-specific make target. This will deploy all the core Kubernetes and Knative resources, and then create `Route` resources for the UIs.
```shell
make deploy-openshift
```

### 5. Accessing the Services

On OpenShift, services are exposed via secure `Routes`. You do not need to use `kubectl port-forward` for external access.

**A. Find the Service URLs:**
- **For Knative Services (like `svc-intake`):** OpenShift Serverless automatically creates a route.
  ```shell
  oc get ksvc svc-intake -n keventmesh
  ```
- **For standard Services (our UIs):** We created routes for them manually.
  ```shell
  oc get route ui-observer -n keventmesh
  oc get route svc-finance-responder -n keventmesh
  ```
  The URLs will be in the `HOST/PORT` column.

**B. Send a Test Request:**
Get the URL for the intake service and use it with `curl`.
```shell
# Get the URL and store it
export INTAKE_URL=$(oc get ksvc svc-intake -n keventmesh -o jsonpath='{.status.url}')

# Send the request
curl -v -X POST $INTAKE_URL \
  -H "Content-Type: application/json" \
  -d '{"content": "My name is Jane Doe and I am locked out of my Gizmo-X account. My email is jane.doe@example.com."}'
  
curl -v -X POST $INTAKE_URL \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hi, I need to dispute a charge on my last invoice, #INV-2025-07. I believe I was overcharged for the premium subscription tier. Can you please look into this and issue a refund? My account email is john.smith@globaltech.com. Thanks, John."
    }
  '
```
You should get a `{"eventId":...}` response.

**C. View the UI Observer:**
Find the route for the UI Observer:
```shell
export UI_URL="https://$(oc get route ui-observer -n keventmesh -o jsonpath='{.spec.host}')"
echo "Access the UI Observer at: $UI_URL"
```
Open the printed URL in your browser. You will see the event flow in real-time.

**D. View the Finance Inbox:**
Find the route for the Finance Responder:
```shell
export FINANCE_URL="https://$(oc get route svc-finance-responder -n keventmesh -o jsonpath='{.spec.host}')"
echo "Access the Finance Inbox at: $FINANCE_URL"
```
Open this URL in your browser. Send a finance-related message to the intake service to see it appear.

### 6. Clean Up
To remove all the deployed resources from your OpenShift cluster, you can use the same `make clean` command, which runs `skaffold delete`. Alternatively, you can delete the entire project:
```shell
oc delete project keventmesh
```


oc adm policy add-scc-to-user anyuid -z default -n keventmesh
oc delete pod -l app=db-customer -n keventmesh
