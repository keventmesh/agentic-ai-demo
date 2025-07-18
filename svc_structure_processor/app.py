import os
import uuid
import json
import logging
import requests
import instructor
from flask import Flask, request, jsonify
from openai import OpenAI
from pydantic import ValidationError

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
def process_content(content: str, message_id: str) -> StructuredObject:
    """Uses LLM to extract structured data from raw text."""

    # Define the payload that will be sent to the LLM
    messages_payload = [
        {"role": "system", "content": "You are a world-class text analysis expert. Extract the customer support email information precisely into the provided JSON format."},
        {"role": "user", "content": content},
    ]

    # --- ADDED: Log the request to the LLM ---
    logging.info(f"[{message_id}] - Sending request to LLM. Payload:\n{json.dumps(messages_payload, indent=2)}")

    try:
        analysis = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            response_model=StructuredObject,
            messages=messages_payload,
        )
        # --- ENHANCED: Log the response from the LLM ---
        logging.info(f"[{message_id}] - Received structured response from LLM:\n{analysis.model_dump_json(indent=2)}")
        return analysis
    except Exception as e:
        # --- ENHANCED: Log the error from the LLM call ---
        logging.error(f"[{message_id}] - LLM call failed: {e}")
        raise  # Re-raise the exception to be caught by the route handler

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_event():
    """Handles incoming CloudEvents from the Broker."""
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    try:
        # The entire request body is the CloudEvent payload
        payload = request.get_json()
        logging.info(f"Received event with subject: {request.headers.get('Ce-Subject')}")

        # Validate and parse the incoming data using our Pydantic model
        incoming_wrapper = OuterWrapper(**payload)
        message_id = incoming_wrapper.message_id
        logging.info(f"[{message_id}] - Received event with subject: {request.headers.get('Ce-Subject')}")

        # Perform the core logic: structuring the content
        structured_data = process_content(incoming_wrapper.content, message_id)
        incoming_wrapper.structured = structured_data

        # NOTE: Using model_dump_json() is crucial if your models have complex types like datetime
        outgoing_payload_str = incoming_wrapper.model_dump_json()

        outgoing_headers = {
            "Ce-Specversion": "1.0",
            "Ce-Type": "com.example.triage.structured",
            "Ce-Source": "/services/structure-processor",
            "Ce-Id": str(uuid.uuid4()),
            "Ce-Subject": message_id,
            "Content-Type": "application/json",
        }

        # Send the new event back to the Broker
        logging.info(f"[{message_id}] - Sending processed event {outgoing_headers['Ce-Id']}")
        # Use `data=` for pre-serialized JSON strings
        response = requests.post(K_SINK, data=outgoing_payload_str, headers=outgoing_headers, timeout=15.0)
        response.raise_for_status()

        logging.info(f"[{message_id}] - Successfully processed and forwarded event.")
        return jsonify({"status": "success"}), 200

    except ValidationError as e:
        logging.error(f"Failed to validate incoming payload: {e}")
        return jsonify({"error": "Invalid payload format"}), 400
    except Exception as e:
        logging.error(f"Error processing event: {e}")
        return jsonify({"error": "Failed to process event"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
