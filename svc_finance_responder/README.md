# Finance Responder Service

This service acts as a simple, real-time "inbox" for the finance department. It subscribes to events that have been routed for financial review (i.e., type `com.example.triage.routed.finance`) and displays them in a web UI.

## Architecture & UI Features

This service is designed for demonstration purposes and uses the same real-time push architecture as the `ui_observer` service.

1.  **Event Subscription:** A Knative `Trigger` is configured to subscribe *only* to events of type `com.example.triage.routed.finance`.

2.  **Backend (Flask):** The `app.py` receives the incoming CloudEvents. It does not process them but immediately relays the event's payload to the UI via Server-Sent Events (SSE).

3.  **Frontend (HTML/JavaScript):** The `inbox.html` page provides an interactive, "Gmail-like" user interface with the following features:
    *   **Real-time Updates:** New messages appear at the top of the inbox instantly without needing a page refresh.
    *   **Accordion View:** Each message is initially shown as a compact summary (sender, subject, timestamp).
    *   **Expandable Details:** Clicking a message summary expands it to reveal the full message content and a formatted view of all the structured data extracted by the AI.
    *   **Visual Alerts:** Messages flagged for escalation are clearly marked with a red **"ESCALATED"** tag, allowing for immediate prioritization.

## Configuration

The service is configured using the following environment variable:

-   **`PORT`**: The network port on which the web server will listen.
    -   **Required**: No
    -   **Default**: `8080`

## Usage on Kubernetes

Once the system is deployed with `make deploy`, you can access the Finance Inbox UI.

1.  Port-forward the service to your local machine:
    ```shell
    kubectl port-forward -n keventmesh svc/svc-finance-responder 8888:80
    ```

2.  Open your web browser to **`http://localhost:8888`**. The page will be empty initially.

3.  Send a message to the `svc-intake` that is likely to be routed to finance (e.g., a message about billing or an invoice). As the event flows through the system and is routed by the `svc-router`, it will appear in real-time on the Finance Inbox UI.

## Local Development

You can run and test this service in isolation without deploying the full system.

1.  Make sure you have set up your local Python environment, as described in the [root README.md](../README.md).

2.  In a terminal, run the Flask application. We'll use port `8888` to avoid conflicts.
    ```bash
    PORT=8888 python app.py
    ```

3.  Open your web browser to **`http://localhost:8888`**. The inbox will be empty.

4.  In a new terminal, use `curl` to send a simulated CloudEvent to the running service. This mimics the Knative Broker delivering an event.

    ```bash
    curl -X POST http://localhost:8888/ \
      -H "Content-Type: application/json" \
      -H "Ce-Specversion: 1.0" \
      -H "Ce-Type: com.example.triage.routed.finance" \
      -H "Ce-Source: /test-script" \
      -H "Ce-Id: test-event-finance-001" \
      -H "Ce-Subject: local-message-abc-123" \
      -d '{
        "message_id": "local-message-abc-123",
        "content": "Hello, I am writing to dispute a charge on my latest invoice #INV-2025-07. I believe I was overcharged for the premium subscription. Can you please look into this?",
        "metadata": {},
        "timestamp": "2025-08-20T10:00:00.000000",
        "structured": {
            "reason": "Billing dispute on invoice #INV-2025-07",
            "sentiment": "negative",
            "company_id": "C-123",
            "company_name": "Global Tech Inc.",
            "country": "USA",
            "customer_name": "John Smith",
            "email_address": "john.smith@globaltech.com",
            "phone": "1-800-555-1234",
            "product_name": "Gizmo-X",
            "escalate": true
        },
        "route": "finance",
        "support": null,
        "website": null,
        "finance": null,
        "comment": null,
        "error": []
      }'
    ```

5.  After running the `curl` command, you should instantly see a new message summary appear in the inbox. Click on it to expand and see the full details.
