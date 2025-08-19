import os
import uuid
import logging
import instructor
import httpx # Import httpx
from flask import Flask, request, jsonify
from openai import OpenAI
from pydantic import ValidationError

# Assuming your models are in a shared 'models.py' file
# This service needs OuterWrapper, SelectedRoute, and the Route enum
from models import OuterWrapper, SelectedRoute, Route

# --- Configuration ---
app = Flask(__name__)
# The main application logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the log level for libraries for detailed request/response info
logging.getLogger("openai").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.DEBUG) # This will log the raw LLM request

APP_PORT = int(os.getenv("PORT", "8080"))
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY', "not-needed")
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "not-set")

if not LLM_API_BASE_URL:
    raise SystemExit("LLM_API_BASE_URL environment variable is not set.")

# This function will be called for every response received by the httpx client.
def log_response(response):
    response.read()
    logging.info(f"LLM Response Body: {response.text}")

# --- Message Processor Class ---
class MessageProcessor:
    def __init__(self):
        """Initializes the processor and the LLM client."""
        http_client = httpx.Client(event_hooks={"response": [log_response]})

        # Patch the OpenAI client with instructor
        self.client = instructor.patch(OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE_URL,
            http_client=http_client
        ))
        logging.info(f"LLM client configured for model '{LLM_MODEL_NAME}' at '{LLM_API_BASE_URL}'")

    def process(self, message: OuterWrapper) -> OuterWrapper:
        """
        Takes an OuterWrapper, uses an LLM to classify its content into a route,
        and updates the 'route' field.
        """
        try:
            logging.info(f"[{message.message_id}] - Starting LLM routing classification.")

            # Use instructor to get a structured response
            selection = self.client.chat.completions.create(
                model=LLM_MODEL_NAME,
                response_model=SelectedRoute,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI-powered message classifier for an enterprise support system. Your task is to analyze email messages and determine the most appropriate team for handling them:
- **Support**: Issues related to technical support, product usage, and troubleshooting.
- **Finance**: Questions about billing, invoices, receipts, payments, refunds, or financial disputes.
- **Website**: Issues related to website functionality, login problems, password reset, account access, or technical errors on the website.
- **Unknown**: If the message does not fit into any of the above categories or lacks sufficient context to classify accurately."""
                    },
                    {
                        "role": "user",
                        "content": f"Classify the following email message and determine the appropriate routing category.\n\nMESSAGE:\n{message.content}",
                    },
                ],
                temperature=0.0
            )

            logging.info(f"[{message.message_id}] - Successfully classified route: {selection.route.value}")
            message.route = selection.route

        except Exception as e:
            error_msg = f"Router LLM call failed: {e}"
            logging.error(f"[{message.message_id}] - {error_msg}")
            message.error.append(error_msg)
            message.route = Route.unknown # Default to unknown on failure

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
    Receives an event, classifies its content, and replies with a new event
    with a type corresponding to the chosen route.
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

    # Determine the outgoing event type based on the classification
    if processed_wrapper.route == Route.support:
        event_type = "com.example.triage.routed.support"
    elif processed_wrapper.route == Route.finance:
        event_type = "com.example.triage.routed.finance"
    elif processed_wrapper.route == Route.website:
        event_type = "com.example.triage.routed.website"
    else: # Covers Route.unknown and any failure case
        event_type = "com.example.triage.review.required"
        logging.warning(f"[{processed_wrapper.message_id}] - Route is '{processed_wrapper.route.value}'. Routing for review.")

    # Construct the CloudEvent headers for the HTTP response.
    response_headers = {
        "Ce-Specversion": "1.0",
        "Ce-Type": event_type,
        "Ce-Source": "/services/router-processor",
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
