# Structure Processor Service

This service subscribes to `com.example.triage.intake.new` events from the Knative Broker. It uses an OpenAI-compatible Large Language Model (LLM) to extract structured information from the raw message content.

## Logic

1.  Receives a CloudEvent containing the `OuterWrapper` payload.
2.  Takes the `content` field from the payload.
3.  Sends the content to an LLM with a prompt instructing it to extract specific fields (name, email, reason, etc.) into a JSON object that matches the `StructuredObject` Pydantic model.
4.  It populates the `structured` field in the `OuterWrapper` with the LLM's response.
5.  It publishes a *new* CloudEvent with the modified payload and an updated type (`com.example.triage.structured`) back to the Broker for downstream processing.

## Configuration

The service is configured using the following environment variables:

-   **`PORT`**: The network port on which the web server will listen. (Default: `8080`)
-   **`K_SINK`**: The destination URL for outgoing CloudEvents, injected by Knative.
-   **`LLM_API_BASE_URL`**: The base URL of the OpenAI-compatible inference server.
-   **`LLM_API_KEY`**: The API key for the inference server (can be a dummy value for local models).
-   **`LLM_MODEL_NAME`**: The name of the model to use for extraction.
