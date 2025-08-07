# Guardian Processor Service

This service acts as a content safety gate. It subscribes to `com.example.triage.intake.new` events from the Knative Broker and uses an OpenAI-compatible Large Language Model (LLM) to check the message content for various types of harmful or undesirable content.

## Logic

1.  Receives a CloudEvent containing the `OuterWrapper` payload.
2.  Takes the `content` field from the payload.
3.  For each harm category defined (e.g., `violence`, `profanity`, `social_bias`), it sends the content to an LLM with a prompt asking it to classify if the content contains that specific harm. The model is instructed to respond with a simple "Yes" or "No".
4.  If the LLM responds with "Yes" for any harm, a descriptive error string (e.g., `guardian:detected:profanity`) is appended to the `error` list within the `OuterWrapper`.
5.  It publishes a *new* CloudEvent with the (potentially modified) payload and an updated type back to the Broker.
    *   If any harms were detected, the event type is set to `com.example.triage.review.required`, routing it for manual review.
    *   If the content is clean, the event type is set to `com.example.triage.guardian.passed`, allowing it to proceed to the next stage (e.g., the structure processor).

## Configuration

The service is configured using the following environment variables:

-   **`PORT`**: The network port on which the web server will listen. (Default: `8080`)
-   **`K_SINK`**: The destination URL for outgoing CloudEvents, injected by Knative.
-   **`LLM_API_BASE_URL`**: The base URL of the OpenAI-compatible inference server.
-   **`LLM_API_KEY`**: The API key for the inference server (can be a dummy value for local models).
-   **`LLM_MODEL_NAME`**: The name of the model to use for classification. Should be a model fine-tuned or prompted for safety checks.

## How to run locally

-   Make sure you have set up your local Python environment, as described in the main project README.

-   Run the Flask application in a terminal. Use a different port if running other services simultaneously.
    ```bash
     K_SINK=<your-event-catcher-or-broker> PORT=8082 LLM_API_BASE_URL=<your-LLM-server> LLM_API_KEY=<your-LLM-api-key> LLM_MODEL_NAME=<your-guardian-model-name> python guardian-processor.py
    # e.g. K_SINK=https://keventmesh-agentic-demo.requestcatcher.com/guardian-processor-output PORT=8082 LLM_API_BASE_URL="http://localhost:11434/v1" LLM_API_KEY="not-needed" LLM_MODEL_NAME="granite3-guardian:8b-fp16" python guardian-processor.py
    ```

-   In a new terminal, use `curl` to send a JSON payload to the service.

### Example 1: Clean Message (Passes)

This message should pass all guardian checks.

```bash
curl -X POST http://localhost:8082/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.intake.new" \
  -H "Ce-Source: /manual-test" \
  -H "Ce-Id: manual-event-clean" \
  -H "Ce-Subject: manual-message-clean" \
  -d '{
  "message_id": "manual-message-clean",
  "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. My email is jane.doe@example.com.",
  "metadata": {}, "timestamp": "2025-07-18T19:56:12.762422", "structured": null, "route": null, "support": null, "website": null, "finance": null, "comment": null, "error": []
  }'
```

If successful, you will receive a `{"status":"success"}` response, and an event with type `com.example.triage.guardian.passed` will be sent to the `K_SINK`. The `error` array in the payload will be empty.

### Example 2: Harmful Message (Fails)

This message contains profanity and should be flagged for review.

```bash
curl -X POST http://localhost:8082/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.intake.new" \
  -H "Ce-Source: /manual-test" \
  -H "Ce-Id: manual-event-harmful" \
  -H "Ce-Subject: manual-message-harmful" \
  -d '{
  "message_id": "manual-message-harmful",
  "content": "This is the worst damn service I have ever used. I am so angry. If you morons dont fix my account immediately, there will be hell to pay.",
  "metadata": {}, "timestamp": "2025-07-18T20:10:00.000000", "structured": null, "route": null, "support": null, "website": null, "finance": null, "comment": null, "error": []
  }'
```

You will still receive a `{"status":"success"}` response. However, the event sent to the `K_SINK` will look like this, with a different type and an error added to the payload:

```http
POST /guardian-processor-output HTTP/1.1
Host: keventmesh-agentic-demo.requestcatcher.com
Accept: */*
Accept-Encoding: gzip, deflate
Ce-Id: 5d1baf9a-c8e9-4a0b-93e5-c26d7f8a1b2c
Ce-Source: /services/guardian-processor
Ce-Specversion: 1.0
Ce-Subject: manual-message-harmful
Ce-Type: com.example.triage.review.required
Content-Type: application/json
...

{
    "message_id": "manual-message-harmful",
    "content": "This is the worst damn service I have ever used. I am so angry. If you morons dont fix my account immediately, there will be hell to pay.",
    "metadata": {},
    "timestamp": "2025-07-18T20:10:00",
    "structured": null,
    "route": null,
    "support": null,
    "website": null,
    "finance": null,
    "comment": null,
    "error": [
        "guardian:detected:profanity"
    ]
}
```
