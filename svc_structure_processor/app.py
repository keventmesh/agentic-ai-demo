import os
import uuid
import logging
import requests
import instructor
import httpx # Import httpx
from flask import Flask, request, jsonify
from openai import OpenAI
from pydantic import ValidationError

from models import OuterWrapper, StructuredObject

# --- Configuration ---
app = Flask(__name__)
# The main application logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the log level for the libraries
# We'll see our own custom logging plus the request logging from httpx
logging.getLogger("openai").setLevel(logging.INFO) # Keep this at INFO
logging.getLogger("httpx").setLevel(logging.DEBUG) # This will log the request

APP_PORT = int(os.getenv("PORT", "8080"))
K_SINK = os.getenv('K_SINK')
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY', "not-needed")
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "not-set")

if not K_SINK:
    raise SystemExit("K_SINK environment variable is not set.")
if not LLM_API_BASE_URL:
    raise SystemExit("LLM_API_BASE_URL environment variable is not set.")

# This function will be called for every response received by the httpx client.
def log_response(response):
    # This ensures the response is read before we try to log it.
    response.read()
    # The 'response.text' contains the full JSON body from the LLM.
    logging.info(f"LLM Response Body: {response.text}")

# --- Message Processor Class ---
class MessageProcessor:
    def __init__(self):
        """Initializes the processor and the LLM client."""

        # Create a custom httpx client with our logging hook
        http_client = httpx.Client(
            event_hooks={"response": [log_response]}
        )

        # Pass the custom client to OpenAI
        self.client = instructor.patch(OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE_URL,
            http_client=http_client # Use our custom client
        ))
        logging.info(f"LLM client configured for model '{LLM_MODEL_NAME}' at '{LLM_API_BASE_URL}'")

    def process(self, message: OuterWrapper) -> OuterWrapper:
        """
        Takes an OuterWrapper, attempts to add structured data using an LLM,
        and returns the (potentially modified) wrapper.
        """
        try:
            logging.info(f"[{message.message_id}] - Starting LLM structure processing.")
            analysis = self.client.chat.completions.create(
                model=LLM_MODEL_NAME,
                response_model=StructuredObject,
                messages=[
                    {"role": "system", "content": "You are a world-class text analysis expert. Extract the information precisely into the provided JSON format. The message is a customer support email."},
                    {"role": "user", "content": message.content},
                ],
            )
            logging.info(f"[{message.message_id}] - Successfully extracted structure: {analysis.model_dump_json(indent=2)}")
            message.structured = analysis
        except Exception as e:
            error_msg = f"LLM call failed: {e}"
            logging.error(f"[{message.message_id}] - {error_msg}")
            message.error.append(error_msg)
        return message

    def send_cloudevent(self, payload: dict, event_type: str, subject: str):
        """Constructs and sends a CloudEvent to the configured K_SINK."""
        event_id = str(uuid.uuid4())
        headers = {
            "Ce-Specversion": "1.0",
            "Ce-Type": event_type,
            "Ce-Source": "/services/structure-processor",
            "Ce-Id": event_id,
            "Ce-Subject": subject,
            "Content-Type": "application/json",
        }
        try:
            logging.info(f"[{subject}] - Sending event {event_id} with type {event_type}")
            # We use model_dump_json() to correctly handle datetime objects
            json_payload_string = OuterWrapper(**payload).model_dump_json()
            response = requests.post(K_SINK, data=json_payload_string, headers=headers, timeout=15.0)
            response.raise_for_status()
            logging.info(f"[{subject}] - Event {event_id} accepted by Broker.")
        except requests.exceptions.RequestException as e:
            logging.error(f"[{subject}] - Failed to send event to Broker: {e}")
            raise

# --- Global Processor Instance ---
processor = MessageProcessor()

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_event():
    """
    This function acts as a single iteration of a consumer loop.
    It receives an event, processes it, and sends a new event.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    try:
        incoming_payload = request.get_json()
        incoming_wrapper = OuterWrapper(**incoming_payload)
        logging.info(f"[{incoming_wrapper.message_id}] - Received event from Broker.")

    except (ValidationError, TypeError) as e:
        logging.error(f"Failed to parse incoming event payload: {e}")
        return jsonify({"error": "Bad request: payload does not match expected schema"}), 400

    processed_wrapper = processor.process(incoming_wrapper)

    try:
        if processed_wrapper.structured:
            event_type = "com.example.triage.structured"
        else:
            event_type = "com.example.triage.guardian-failed"
            logging.warning(f"[{processed_wrapper.message_id}] - No structure extracted. Routing to failure path.")

        processor.send_cloudevent(
            payload=processed_wrapper.model_dump(),
            event_type=event_type,
            subject=processed_wrapper.message_id
        )
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"[{processed_wrapper.message_id}] - A critical error occurred after processing: {e}")
        return jsonify({"error": "Failed to forward processed event"}), 500

if __name__ == '__main__':
    logging.info(f"Service starting and listening on port {APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
