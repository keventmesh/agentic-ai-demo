import os
import uuid
import logging
import requests
import instructor
from flask import Flask, request, jsonify
from openai import OpenAI

# This import now works cleanly because of the project structure
from models import OuterWrapper, StructuredObject

# --- Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

APP_PORT = int(os.getenv("PORT", "8080"))
K_SINK = os.getenv('K_SINK')
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY', "not-needed")
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "not-set")

if not K_SINK:
    raise SystemExit("K_SINK environment variable is not set.")
if not LLM_API_BASE_URL:
    raise SystemExit("LLM_API_BASE_URL environment variable is not set.")

# Patch the OpenAI client with instructor
client = instructor.patch(OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_API_BASE_URL
))

logging.info(f"Service is listening on port: {APP_PORT}")
logging.info(f"Outgoing events will be sent to: {K_SINK}")
logging.info(f"Using LLM model '{LLM_MODEL_NAME}' at '{LLM_API_BASE_URL}'")

# --- Business Logic ---
def process_content(content: str) -> StructuredObject:
    """Uses LLM to extract structured data from raw text."""
    try:
        logging.info("Attempting to extract structure from content...")
        analysis = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            response_model=StructuredObject,
            messages=[
                {"role": "system", "content": "You are a world-class text analysis expert. Extract the customer support email information precisely into the provided JSON format."},
                {"role": "user", "content": content},
            ],
        )
        logging.info(f"Successfully extracted structure: {analysis.model_dump_json()}")
        return analysis
    except Exception as e:
        logging.error(f"LLM call failed: {e}")
        raise  # Re-raise the exception to be caught by the route handler

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_event():
    """Handles incoming CloudEvents from the Broker."""
    if not request.is_json:
        return jsonify({"error": "Request must be be application/json"}), 415

    try:
        # The entire request body is the CloudEvent payload
        payload = request.get_json()
        logging.info(f"Received event with subject: {request.headers.get('Ce-Subject')}")

        # Validate and parse the incoming data using our Pydantic model
        incoming_wrapper = OuterWrapper(**payload)

        # Perform the core logic: structuring the content
        structured_data = process_content(incoming_wrapper.content)
        incoming_wrapper.structured = structured_data

        # Prepare the outgoing event
        outgoing_payload = incoming_wrapper.model_dump()
        outgoing_headers = {
            "Ce-Specversion": "1.0",
            "Ce-Type": "com.example.triage.structured",  # The new event type
            "Ce-Source": "/services/structure-processor",
            "Ce-Id": str(uuid.uuid4()),
            "Ce-Subject": incoming_wrapper.message_id,  # Correlate with the original message
            "Content-Type": "application/json",
        }

        # Send the new event back to the Broker
        logging.info(f"Sending processed event {outgoing_headers['Ce-Id']}")
        response = requests.post(K_SINK, json=outgoing_payload, headers=outgoing_headers, timeout=15.0)
        response.raise_for_status()

        logging.info("Successfully processed and forwarded event.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        # If any step fails, log the error and return a server error.
        # Knative Broker will attempt to redeliver the event.
        logging.error(f"Error processing event: {e}")
        return jsonify({"error": "Failed to process event"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
