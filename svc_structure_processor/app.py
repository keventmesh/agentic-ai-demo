import os
import uuid
import logging
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
LLM_API_BASE_URL = os.getenv('LLM_API_BASE_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY', "not-needed")
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', "not-set")

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

# --- Global Processor Instance ---
processor = MessageProcessor()

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_event():
    """
    This function acts as the event handler using the request-reply pattern.
    It receives an event, processes it, and replies with a new event in the
    HTTP response, which Knative Eventing will then route.
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

    # Process the message to produce the data for the new event
    processed_wrapper = processor.process(incoming_wrapper)

    # Determine the type of the event we are replying with
    if processed_wrapper.structured:
        event_type = "com.example.triage.structured"
    else:
        event_type = "com.example.triage.guardian-failed"
        logging.warning(f"[{processed_wrapper.message_id}] - No structure extracted. Routing to failure path.")

    # Construct the CloudEvent headers for the HTTP response.
    # Knative will interpret this HTTP response as a new event.
    response_headers = {
        "Ce-Specversion": "1.0",
        "Ce-Type": event_type,
        "Ce-Source": "/services/structure-processor",
        "Ce-Id": str(uuid.uuid4()),
        "Ce-Subject": processed_wrapper.message_id,
    }

    # The body of the response becomes the data payload of the new CloudEvent.
    # We use model_dump(mode='json') to get a dict with JSON-compatible types.
    # This correctly serializes datetime objects to ISO 8601 strings.
    response_payload = processed_wrapper.model_dump(mode='json')

    # By returning a payload and headers, we are sending a new event back
    # to the Knative component (e.g., Broker) that sent the original request.
    # jsonify will handle serializing the payload and setting the Content-Type.
    logging.info(f"[{processed_wrapper.message_id}] - Replying with new event of type '{event_type}'.")
    return jsonify(response_payload), 200, response_headers


if __name__ == '__main__':
    logging.info(f"Service starting and listening on port {APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
