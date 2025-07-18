# UI Observer Service

This service provides a real-time web UI to visualize the flow of events through the system, making it an essential component for live demonstrations. It listens for every event published to the Knative Broker and pushes them to a web browser using Server-Sent Events (SSE).

The UI dynamically creates a "card" for each unique `message_id` and then populates that card with the sequence of events related to that message, providing a clear, real-time "swimlane" view of each message's journey.

## Architecture

1.  **Event Subscription:** A Knative `Trigger` without any filters is configured for this service. This means it receives a copy of *every* event that passes through the `default` Broker.

2.  **Backend (Flask):** The `app.py` receives incoming CloudEvents via a standard `POST` request. Instead of processing the event's content, it simply extracts key details (event type, subject) and the full payload.

3.  **Real-time Push (SSE):** The backend then publishes this event data to a Server-Sent Events (SSE) stream on the `/stream` endpoint. SSE is a simple, efficient protocol for servers to push data to web clients.

4.  **Frontend (HTML/JavaScript):** The `index.html` page contains JavaScript that connects to the `/stream` endpoint. When it receives a new event from the stream, it finds the appropriate card on the page (based on `message_id`) and dynamically adds the new event to it.

## Configuration

The service is configured using the following environment variable:

-   **`PORT`**: The network port on which the web server will listen.
    -   **Required**: No
    -   **Default**: `8080`

## How to Run Locally (as part of the full demo)

To see the UI in action, you should run it while also having the other services available to generate events.

1.  Make sure you have set up your local Python environment as described in the [root README.md](../README.md).

2.  In a dedicated terminal, run the UI service using `gunicorn`:
    ```bash
    # You can set a custom port if you like
    PORT=9999 python app.py
    ```

3.  Open your web browser to **`http://localhost:8082`**. The page will be blank initially.

4.  In another terminal, send a request to the `intake-service` (running on its own port, e.g., 8080) to start the event flow. As events are generated, they will appear in real-time on the UI page in your browser.

## How to Test in Isolation (with `curl`)

To test just the UI service without running the rest of the system, you can manually send it a simulated CloudEvent using `curl`. This is useful for testing frontend changes.

1.  Start the service locally as described above.

2.  Open your browser to `http://localhost:9999`.

3.  In a separate terminal, run the following `curl` command. This command simulates the Knative Broker sending a `com.example.triage.structured` event.

    ```sh
    curl -X POST http://localhost:9999/ \
    -H "Content-Type: application/json" \
    -H "Ce-Specversion: 1.0" \
    -H "Ce-Type: com.example.triage.structured" \
    -H "Ce-Source: /test-script" \
    -H "Ce-Id: test-event-001" \
    -H "Ce-Subject: message-journey-42" \
    -d '{
        "message_id": "message-journey-42",
        "content": "Original customer message here...",
        "structured": {
            "reason": "Account Lockout",
            "customer_name": "Jane Doe",
            "email_address": "jane.doe@example.com",
            "product_name": "Gizmo-X",
            "sentiment": "negative",
            "escalate": true
        },
        "error": []
    }'
    ```

4.  After running the command, you should instantly see a new card for "message-journey-42" appear in your browser window, containing the `com.example.triage.structured` event you just sent.
