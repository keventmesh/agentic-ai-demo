import os
import uuid
import logging
import psycopg2
from psycopg2 import sql
from flask import Flask, request, jsonify
from pydantic import ValidationError

from models import OuterWrapper

# --- Configuration ---
app = Flask(__name__)
# The main application logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

APP_PORT = int(os.getenv("PORT", "8080"))

# Database Configuration
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Validate required environment variables
if not all([DB_NAME, DB_USER, DB_PASSWORD, DB_HOST]):
    raise SystemExit("One or more database environment variables (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST) are not set.")

# --- Message Processor Class ---
class MessageProcessor:
    def __init__(self):
        """Initializes the processor."""
        logging.info("Customer Lookup Processor initialized.")
        self.db_conn_string = f"dbname='{DB_NAME}' user='{DB_USER}' password='{DB_PASSWORD}' host='{DB_HOST}' port='{DB_PORT}'"
        # Test connection on startup
        try:
            with psycopg2.connect(self.db_conn_string) as conn:
                logging.info(f"Successfully connected to database '{DB_NAME}' at {DB_HOST}:{DB_PORT}.")
        except psycopg2.OperationalError as e:
            logging.error(f"FATAL: Could not connect to database on startup: {e}")
            raise SystemExit(f"Database connection failed: {e}")


    def process(self, message: OuterWrapper) -> OuterWrapper:
        """
        Takes an OuterWrapper, looks up customer details from a database using
        the email in the 'structured' field, and enriches the message.
        """
        if not message.structured or not message.structured.email_address:
            error_msg = "customer-lookup:missing-email"
            logging.warning(f"[{message.message_id}] - Cannot perform lookup. No structured email found. Appending error: {error_msg}")
            message.error.append(error_msg)
            return message

        email = message.structured.email_address
        logging.info(f"[{message.message_id}] - Starting customer lookup for email: {email}")

        connection = None
        cursor = None
        try:
            connection = psycopg2.connect(self.db_conn_string)
            cursor = connection.cursor()

            query = sql.SQL("""
                            SELECT customer_id, company_name, contact_name, country, phone
                            FROM customers WHERE contact_email = %s
                            """)
            cursor.execute(query, (email,))
            customer_record = cursor.fetchone()

            if customer_record:
                # Unpack the record
                (customer_id, company_name, contact_name, country, phone) = customer_record
                logging.info(f"[{message.message_id}] - Found customer: {customer_id} - {company_name}")

                # Enrich the structured data in the message
                message.structured.company_id = customer_id
                # Only overwrite if the DB value is more specific
                if company_name: message.structured.company_name = company_name
                if contact_name: message.structured.customer_name = contact_name
                if country: message.structured.country = country
                if phone: message.structured.phone = phone

            else:
                error_msg = "customer-lookup:not-found"
                logging.warning(f"[{message.message_id}] - Customer with email '{email}' not found. Appending error: {error_msg}")
                message.error.append(error_msg)

        except Exception as e:
            error_msg = f"Database query failed: {e}"
            logging.error(f"[{message.message_id}] - {error_msg}")
            message.error.append(error_msg)
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return message

# --- Global Processor Instance ---
processor = MessageProcessor()

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_event():
    """
    Receives an event with structured data, enriches it with customer info,
    and replies with a new event indicating success or failure.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    try:
        incoming_payload = request.get_json()
        incoming_wrapper = OuterWrapper(**incoming_payload)
        logging.info(f"[{incoming_wrapper.message_id}] - Received event from Broker.")
        original_error_count = len(incoming_wrapper.error)

    except (ValidationError, TypeError) as e:
        logging.error(f"Failed to parse incoming event payload: {e}")
        return jsonify({"error": "Bad request: payload does not match expected schema"}), 400

    processed_wrapper = processor.process(incoming_wrapper)

    # Check if the lookup process added any new errors
    if len(processed_wrapper.error) > original_error_count:
        event_type = "com.example.triage.review.required"
        logging.warning(f"[{processed_wrapper.message_id}] - Customer lookup failed or incomplete. Routing for review.")
    else:
        event_type = "com.example.triage.customer.found"
        logging.info(f"[{processed_wrapper.message_id}] - Customer data enriched successfully. Routing for triage.")

    # Construct the CloudEvent headers for the HTTP response.
    response_headers = {
        "Ce-Specversion": "1.0",
        "Ce-Type": event_type,
        "Ce-Source": "/services/customer-lookup-processor",
        "Ce-Id": str(uuid.uuid4()),
        "Ce-Subject": processed_wrapper.message_id,
    }

    # The body of the response becomes the data payload of the new CloudEvent.
    response_payload = processed_wrapper.model_dump(mode='json')

    # Reply directly with the new event payload and headers.
    logging.info(f"[{processed_wrapper.message_id}] - Replying with new event of type '{event_type}'.")
    return jsonify(response_payload), 200, response_headers


if __name__ == '__main__':
    logging.info(f"Service starting and listening on port {APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
