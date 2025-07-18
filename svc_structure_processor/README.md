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

## How to run locally

- Make sure you have set up your local Python environment, as described in the [README](../README.md).

- Run the Flask application:
    ```bash
     K_SINK=<your-Kafka-broker> PORT=8081 LLM_API_BASE_URL=<your-LLM-server> LLM_API_KEY=<your-LLM-api-key> LLM_MODEL_NAME=<your-LLM-model-name> python app.py
    # e.g. K_SINK=https://keventmesh-agentic-demo.requestcatcher.com/structure-processor-output PORT=8080 LLM_API_BASE_URL="http://localhost:11434/v1" LLM_API_KEY="none" LLM_MODEL_NAME="llama3.2:1b" python app.py
    ```

-  In a new terminal, use `curl` to send a JSON payload to the service.
    ```bash
    curl -X POST http://localhost:8081/ \
      -H "Content-Type: application/json" \
      -H "Ce-Specversion: 1.0" \
      -H "Ce-Type: com.example.triage.intake.new" \
      -H "Ce-Source: /manual-test" \
      -H "Ce-Id: manual-event-12345" \
      -H "Ce-Subject: manual-message-67890" \
      -d '{
      "message_id": "manual-message-67890",
      "content": "Hello team, my name is Alice. The battery on my Quantum Widget 3000 seems to be draining far too quickly. Can you advise? My email is alice.w@email-provider.com",
      "metadata": {},
      "structured": null,
      "route": null,
      "support": null,
      "website": null,
      "finance": null,
      "error": []
      }'
    ```

   If successful, you will receive a response like:
    ```json
    {"status":"event accepted","eventId":"...uuid..."}
    ```

This indicates the event has been successfully sent to the Broker.
