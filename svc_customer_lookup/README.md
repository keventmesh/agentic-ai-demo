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
    PORT=8083 \
    DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres \
    python app.py
    # e.g.   PORT=8083 DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres python app.py
    # or     PORT=8083 DB_HOST=localhost DB_PORT=5432 DB_NAME=customer DB_USER=postgres DB_PASSWORD=postgres python app.py
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

If successful, you will receive an output like this:
```text
HTTP/1.1 200 OK
...
Ce-Type: com.example.triage.customer.found
Ce-Source: /services/customer-lookup-processor
Ce-Id: 4160c1d7-e203-489d-860e-47cc8b55c29e
...
```

```json
{
  "comment": null,
  "content": "Hello, my name is Jane Doe. I am writing because I am completely locked out of my account for the Gizmo-X product. I have tried the password reset link five times and it is not working. I am really frustrated because I have a deadline today and need to access my files. Can someone please help me ASAP? My email is jane.doe@example.com.",
  "error": [],
  "finance": null,
  "message_id": "35bd56f4-7fe5-455f-bf82-2c4ec20d3ef5",
  "metadata": {},
  "route": null,
  "structured": {
    "company_id": "C-456",
    "company_name": "Acme Corp.",
    "country": "USA",
    "customer_name": "Jane Doe",
    "email_address": "jane.doe@example.com",
    "escalate": false,
    "phone": "1-800-555-4567",
    "product_name": "Gizmo-X",
    "reason": "Locked out of account with unsuccessful reset attempts",
    "sentiment": "negative"
  },
  "support": null,
  "timestamp": "2025-08-19T10:09:20.895425",
  "website": null
}
```

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

If successful, you will receive an output like this, and the payload will contain an error:
```text
HTTP/1.1 200 OK
...
Ce-Type: com.example.triage.review.required
Ce-Source: /services/customer-lookup-processor
Ce-Id: 4160c1d7-e203-489d-860e-47cc8b55c29e
...
```

```json
{
  ...
  "error": [
    "customer-lookup:not-found"
  ],
  ...
}
```
