# Intake Service

This service is the entry point for the AI Message Triage pipeline. It's a simple Flask web application that accepts a JSON payload, wraps its content into a CloudEvent, and sends it to a Knative Broker for asynchronous processing.

## Configuration

The service is configured using the following environment variables:

-   **`PORT`**: The network port on which the web server will listen.
    -   **Required**: No
    -   **Default**: `8080`

-   **`K_SINK`**: The full destination URL where the service should send outgoing CloudEvents.
    -   **Required**: Yes
    -   **Default**: None. The application will fail to start if this is not set.

## Architecture

This service is deployed as a standard Kubernetes `Deployment` and `Service`. It is integrated with Knative Eventing using a `SinkBinding`, which automatically injects the `K_SINK` environment variable. This variable provides the destination URL for the events (the Broker's ingress).

-   **`app.py`**: The Flask application logic.
-   **`config/`**: Contains the Kubernetes resources.

## API Contract

-   **Endpoint**: `POST /`
-   **Content-Type**: `application/json`
-   **Request Body**:
    ```json
    {
      "content": "The raw text message to be processed."
    }
    ```

## How to run locally

- Make sure you have set up your local Python environment, as described in the [README](../README.md).

- Run the Flask application:
    ```bash
     K_SINK=<your-Kafka-broker> PORT=8080 python app.py
    # e.g.   K_SINK=http://broker-ingress.knative-eventing.svc.cluster.local            PORT=8080   python app.py
    # or     K_SINK=https://keventmesh-agentic-demo.requestcatcher.com/intake-output    PORT=8080   python app.py
    ```

-  In a new terminal, use `curl` to send a JSON payload to the service.
    ```bash
    curl -X POST http://localhost:8080/ \
      -H "Content-Type: application/json" \
      -d '{
        "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com."
      }'
    ```

   If successful, you will receive a response like:
    ```json
    {"status":"event accepted","eventId":"...uuid..."}
    ```

This indicates the event has been successfully sent to the Broker.

- The event that's sent will look like this:
    ```
    POST /intake-output HTTP/1.1
    Host: keventmesh-agentic-demo.requestcatcher.com
    Accept: */*
    Accept-Encoding: gzip, deflate
    Ce-Id: c8cf6c69-1d5e-4d76-bf63-91601c6d5d8b
    Ce-Source: /services/svc-intake
    Ce-Specversion: 1.0
    Ce-Subject: c8cf6c69-1d5e-4d76-bf63-91601c6d5d8b
    Ce-Type: com.example.triage.intake.new
    Connection: keep-alive
    Content-Length: 559
    Content-Type: application/json
    User-Agent: python-requests/2.32.3
    
    {
        "message_id":"c8cf6c69-1d5e-4d76-bf63-91601c6d5d8b",
        "content":"Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com.",
        "metadata":{},
        "timestamp":"2025-07-18T19:56:12.762422",
        "structured":null,
        "route":null,
        "support":null,
        "website":null,
        "finance":null,
        "comment":null,
        "error":[]
    }
   ```
