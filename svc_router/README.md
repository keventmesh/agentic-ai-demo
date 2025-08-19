# Router Service

This service subscribes to events for which customer data has been successfully identified (i.e., type `com.example.triage.customer.found`). It uses a Large Language Model (LLM) to classify the message content and determine the appropriate internal department for handling the request.

## Logic

1.  Receives a CloudEvent containing the `OuterWrapper` payload.
2.  It sends the `content` of the message to an LLM with a prompt instructing it to classify the request into one of several predefined categories: `Support`, `Finance`, `Website`, or `Unknown`.
3.  The service uses the `instructor` library to ensure the LLM's response is a val id JSON object matching the `SelectedRoute` Pydantic model.
4.  It populates the `route` field in the `OuterWrapper` with the classification result from the LLM.
5.  It publishes a *new* CloudEvent with the modified payload. The **type** of this new event is determined by the classification:
    *   `Support` -> `com.example.triage.routed.support`
    *   `Finance` -> `com.example.triage.routed.finance`
    *   `Website` -> `com.example.triage.routed.website`
    *   `Unknown` (or if the LLM call fails) -> `com.example.triage.review.required`

## Configuration

The service is configured using the following environment variables:

-   **`PORT`**: The network port on which the web server will listen. (Default: `8080`)
-   **`LLM_API_BASE_URL`**: The base URL of the OpenAI-compatible inference server.
-   **`LLM_API_KEY`**: The API key for the inference server (can be a dummy value for local models).
-   **`LLM_MODEL_NAME`**: The name of the model to use for classification.

## How to run locally

-   Make sure you have set up your local Python environment as described in the main project README.

-   Run the Flask application in a terminal.
    ```bash
    PORT=8084 LLM_API_BASE_URL=<your-LLM-server> LLM_API_KEY=<your-LLM-api-key> LLM_MODEL_NAME=<your-router-model-name> python app.py
    # e.g. PORT=8084 LLM_API_BASE_URL="http://localhost:11434/v1" LLM_API_KEY="none" LLM_MODEL_NAME="gpt-oss:20b" python app.py
    ```

-   In a new terminal, use `curl` to send a JSON payload to the service. The payload should simulate the output from the `customer-lookup` service.

### Example 1: Route to Finance

```bash
curl -i -X POST http://localhost:8084/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.customer.found" \
  -H "Ce-Source: /test" \
  -H "Ce-Id: test-event-finance" \
  -H "Ce-Subject: test-message-finance" \
  -d '{
    "message_id": "test-message-finance",
    "content": "Hello, I am writing to dispute a charge on my latest invoice #INV-2025-07 for Gizmo-X product. I believe I was overcharged for the premium subscription. Can you please look into this and issue a refund? Thanks, John. john.smith@globaltech.com",
    "metadata": {},
    "timestamp": "2025-07-18T19:56:12.762422",
    "structured": {
        "reason": "Billing issue",
        "sentiment": "neutral",
        "company_id": null,
        "company_name": "",
        "country": null,
        "customer_name": "",
        "email_address": "john.smith@globaltech.com",
        "phone": null,
        "product_name": "Gizmo-X",
        "escalate": false
    },
    "route": null,
    "support": null,
    "website": null,
    "finance": null,
    "comment": null,
    "error": []
  }'
```

The service will reply with a new event of type `com.example.triage.routed.finance` and the payload's `route` field set to `"Finance"`:

```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.3 Python/3.11.9
Date: Tue, 19 Aug 2025 12:53:09 GMT
Content-Type: application/json
Content-Length: 776
Ce-Specversion: 1.0
Ce-Type: com.example.triage.routed.finance
Ce-Source: /services/router-processor
Ce-Id: 12b9e34e-a3e4-4d05-bbe0-90cc83581cb4
Ce-Subject: test-message-finance
Connection: close
```
```json
{
  "comment": null,
  "content": "Hello, I am writing to dispute a charge on my latest invoice #INV-2025-07 for Gizmo-X product. I believe I was overcharged for the premium subscription. Can you please look into this and issue a refund? Thanks, John. john.smith@globaltech.com",
  "error": [],
  "finance": null,
  "message_id": "test-message-finance",
  "metadata": {},
  "route": "finance",
  "structured": {
    "company_id": null,
    "company_name": "",
    "country": null,
    "customer_name": "",
    "email_address": "john.smith@globaltech.com",
    "escalate": false,
    "phone": null,
    "product_name": "Gizmo-X",
    "reason": "Billing issue",
    "sentiment": "neutral"
  },
  "support": null,
  "timestamp": "2025-07-18T19:56:12.762422",
  "website": null
}
```

### Example 2: Route to Website

```bash
curl -i -X POST http://localhost:8084/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.customer.found" \
  -H "Ce-Source: /test" \
  -H "Ce-Id: test-event-website" \
  -H "Ce-Subject: test-message-website" \
  -d '{
    "message_id": "test-message-website",
    "content": "I am completely locked out of my account. The password reset link you sent me is not working, it just goes to a blank page. I need to access my files ASAP. jane.doe@example.com",
    "metadata": {},
    "timestamp": "2025-07-18T19:56:12.762422",
    "structured": {
        "reason": "Website issue",
        "sentiment": "neutral",
        "company_id": null,
        "company_name": "",
        "country": null,
        "customer_name": "",
        "email_address": "jane.doe@example.com",
        "phone": null,
        "product_name": "",
        "escalate": false
    },
    "route": null,
    "support": null,
    "website": null,
    "finance": null,
    "comment": null,
    "error": []
  }'
```

The service will reply with a new event of type `com.example.triage.routed.website` and the payload's `route` field set to `"Website"`:

```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.3 Python/3.11.9
Date: Tue, 19 Aug 2025 13:00:55 GMT
Content-Type: application/json
Content-Length: 698
Ce-Specversion: 1.0
Ce-Type: com.example.triage.routed.website
Ce-Source: /services/router-processor
Ce-Id: e5dd8b4c-b1ca-4a66-ad8b-7b3aa2fd9818
Ce-Subject: test-message-website
Connection: close
```
```json
{
  "comment": null,
  "content": "I am completely locked out of my account. The password reset link you sent me is not working, it just goes to a blank page. I need to access my files ASAP. jane.doe@example.com",
  "error": [],
  "finance": null,
  "message_id": "test-message-website",
  "metadata": {},
  "route": "website",
  "structured": {
    "company_id": null,
    "company_name": "",
    "country": null,
    "customer_name": "",
    "email_address": "jane.doe@example.com",
    "escalate": false,
    "phone": null,
    "product_name": "",
    "reason": "Website issue",
    "sentiment": "neutral"
  },
  "support": null,
  "timestamp": "2025-07-18T19:56:12.762422",
  "website": null
}
```

### Example 3: Route to Review (Unknown)

```bash
curl -i -X POST http://localhost:8084/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.customer.found" \
  -H "Ce-Source: /test" \
  -H "Ce-Id: test-event-unknown" \
  -H "Ce-Subject: test-message-unknown" \
  -d '{
    "message_id": "test-message-unknown",
    "content": "Can we schedule a meeting for next Tuesday? It is regarding the partnership opportunity we discussed on the phone last week. My email is partner@corp.com",
    "metadata": {},
    "timestamp": "2025-07-18T19:56:12.762422",
    "structured": {
        "reason": "",
        "sentiment": "neutral",
        "company_id": null,
        "company_name": "",
        "country": null,
        "customer_name": "",
        "email_address": "partner@corp.com",
        "phone": null,
        "product_name": "",
        "escalate": false
    },
    "route": null,
    "support": null,
    "website": null,
    "finance": null,
    "comment": null,
    "error": []
  }'
```

Because this message does not fit the support, finance, or website categories, the service will reply with an event of type `com.example.triage.review.required` and the `route` field set to `"Unknown"`:

```text
HTTP/1.1 200 OK
Server: Werkzeug/3.1.3 Python/3.11.9
Date: Tue, 19 Aug 2025 13:01:35 GMT
Content-Type: application/json
Content-Length: 658
Ce-Specversion: 1.0
Ce-Type: com.example.triage.review.required
Ce-Source: /services/router-processor
Ce-Id: b9aeda77-4b7a-4fbc-b551-b37867a3ec6b
Ce-Subject: test-message-unknown
Connection: close
```
```json
{
  "comment": null,
  "content": "Can we schedule a meeting for next Tuesday? It is regarding the partnership opportunity we discussed on the phone last week. My email is partner@corp.com",
  "error": [],
  "finance": null,
  "message_id": "test-message-unknown",
  "metadata": {},
  "route": "unknown",
  "structured": {
    "company_id": null,
    "company_name": "",
    "country": null,
    "customer_name": "",
    "email_address": "partner@corp.com",
    "escalate": false,
    "phone": null,
    "product_name": "",
    "reason": "",
    "sentiment": "neutral"
  },
  "support": null,
  "timestamp": "2025-07-18T19:56:12.762422",
  "website": null
}
```
