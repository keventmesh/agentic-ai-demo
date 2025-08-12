# Customer Lookup Processor Service

This service subscribes to events that have been successfully processed by the `structure-processor` (i.e., type `com.example.triage.structured`). Its purpose is to enrich the message with known customer information by looking up the customer in a relational database.

## Logic

1.  Receives a CloudEvent containing an `OuterWrapper` payload. This payload is expected to have the `structured` field populated.
2.  It extracts the `email_address` from the `structured` object.
3.  It connects to a PostgreSQL database and queries a `customers` table for a record matching the email address.
4.  **If a matching customer is found:**
    *   It enriches the `structured` object in the payload with data from the database (e.g., `customer_id`, `company_name`, `country`, `phone`).
    *   It publishes a *new* CloudEvent with the enriched payload and the type `com.example.triage.customer.found`.
5.  **If no matching customer is found (or if the incoming email is missing):**
    *   It appends a descriptive error to the `error` list in the payload (e.g., `customer-lookup:not-found`).
    *   It publishes a *new* CloudEvent with the type `com.example.triage.review.required`, routing the message for manual handling as it may be from a new prospect or contain incorrect information.

## Configuration

The service is configured using the following environment variables:

-   **`PORT`**: The network port on which the web server will listen. (Default: `8080`)
-   **`K_SINK`**: The destination URL for outgoing CloudEvents, injected by Knative.
-   **`DB_HOST`**: The hostname or IP address of the PostgreSQL database server.
-   **`DB_PORT`**: The port of the PostgreSQL database server. (Default: `5432`)
-   **`DB_NAME`**: The name of the database to connect to.
-   **`DB_USER`**: The username for the database connection.
-   **`DB_PASSWORD`**: The password for the database connection.

## How to run locally

- Make sure you have set up your local Python environment, as described in the [README](../README.md).
 
- Make sure you have PostgreSQL database instance accessible. Check out the [README.md](../db_customer/README.md) of the `db_customer` service for instructions.

- Run the Flask application in a terminal, providing the necessary database credentials.
    ```bash
    K_SINK=<your-Kafka-broker> PORT=8083 \
    DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres \
    python app.py
    # e.g.   K_SINK=http://broker-ingress.knative-eventing.svc.cluster.local                   PORT=8083 DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres python app.py
    # or     K_SINK=https://keventmesh-agentic-demo.requestcatcher.com/customer-lookup-output  PORT=8083 DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres python app.py
    ```

-   In a new terminal, use `curl` to send a JSON payload to the service. The payload must simulate the output from the `structure-processor`, containing a `structured` object with an `email_address`.

### Example 1: Customer Found (Success)

This `curl` uses an email that exists in our sample data.

```bash
curl -X POST http://localhost:8083/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.structured" \
  -H "Ce-Source: /test" \
  -H "Ce-Id: test-event-found" \
  -H "Ce-Subject: test-message-found" \
  -d '{
    "metadata": {},
    "message_id": "test-message-found",
    "content": "Hi, my login for Gizmo-X is not working. My email is john.smith@globaltech.com",
    "structured": {
        "reason": "Login issue",
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

If successful, you will receive `{"status":"success"}`. The event sent to `K_SINK` will have the type `com.example.triage.customer.found` and the payload's `structured` field will be enriched with data from the database.

### Example 2: Customer Not Found (Review Required)

This `curl` uses an email that does **not** exist in our sample data.

```bash
curl -X POST http://localhost:8083/ \
  -H "Content-Type: application/json" \
  -H "Ce-Specversion: 1.0" \
  -H "Ce-Type: com.example.triage.structured" \
  -H "Ce-Source: /test" \
  -H "Ce-Id: test-event-notfound" \
  -H "Ce-Subject: test-message-notfound" \
  -d '{
    "message_id": "test-message-notfound",
    "content": "Hi, my name is Susan. I am interested in your products. My email is susan.q@newprospect.com",
    "structured": {
        "reason": "Sales inquiry",
        "sentiment": "positive",
        "company_id": null,
        "company_name": "",
        "country": null,
        "customer_name": "Susan",
        "email_address": "susan.q@newprospect.com",
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

You will still receive `{"status":"success"}`. The event sent to `K_SINK` will now have the type `com.example.triage.review.required`, and the payload will contain an error:
```json
{
    "message_id": "test-message-notfound",
    "content": "...",
    "structured": { "..."},
    "error": ["customer-lookup:not-found"]
}
```
