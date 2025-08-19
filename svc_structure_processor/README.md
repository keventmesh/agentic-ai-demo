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
-   **`LLM_API_BASE_URL`**: The base URL of the OpenAI-compatible inference server.
-   **`LLM_API_KEY`**: The API key for the inference server (can be a dummy value for local models).
-   **`LLM_MODEL_NAME`**: The name of the model to use for extraction.

## How to run locally

- Make sure you have set up your local Python environment, as described in the [README](../README.md).

- Run the Flask application:
    ```bash
     PORT=8081 LLM_API_BASE_URL=<your-LLM-server> LLM_API_KEY=<your-LLM-api-key> LLM_MODEL_NAME=<your-LLM-model-name> python app.py
    # e.g. PORT=8080 LLM_API_BASE_URL="http://localhost:11434/v1" LLM_API_KEY="none" LLM_MODEL_NAME="gpt-oss:20b" python app.py
    ```

-  In a new terminal, use `curl` to send a JSON payload to the service.
    ```bash
    curl -i -X POST http://localhost:8081/ \
      -H "Content-Type: application/json" \
      -H "Ce-Specversion: 1.0" \
      -H "Ce-Type: com.example.triage.intake.new" \
      -H "Ce-Source: /manual-test" \
      -H "Ce-Id: manual-event-12345" \
      -H "Ce-Subject: manual-message-67890" \
      -d '{
      "message_id": "manual-message-67890",
      "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com.",
      "metadata": {},
      "timestamp": "2025-07-18T19:56:12.762422",
      "structured": null,
      "route": null,
      "support": null,
      "website": null,
      "finance": null,
      "comment": null,
      "error": []
      }'
    ```

If successful, you will receive a response like:
```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.3 Python/3.11.9
Date: Tue, 19 Aug 2025 08:46:02 GMT
Content-Type: application/json
Content-Length: 901
Ce-Specversion: 1.0
Ce-Type: com.example.triage.structured
Ce-Source: /services/structure-processor
Ce-Id: 28f60682-b3aa-4867-bcf3-03ec3f44ea93
Ce-Subject: manual-message-67890
Connection: close
```
```json
{
  "comment": null,
  "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com.",
  "error": [],
  "finance": null,
  "message_id": "manual-message-67890",
  "metadata": {},
  "route": null,
  "structured": {
    "company_id": null,
    "company_name": null,
    "country": null,
    "customer_name": "Jane Doe",
    "email_address": "jane.doe@example.com",
    "escalate": true,
    "phone": null,
    "product_name": "Gizmo-X",
    "reason": "account locked out, unable to reset password",
    "sentiment": "negative"
  },
  "support": null,
  "timestamp": "2025-07-18T19:56:12.762422",
  "website": null
}
```
