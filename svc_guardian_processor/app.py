import os
import uuid
import logging
import httpx # Import httpx
from flask import Flask, request, jsonify
from openai import OpenAI
from pydantic import ValidationError

from models import OuterWrapper

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

# This list defines all the harm categories the guardian will check for.
# It's easily extensible.
HARMS_TO_CHECK = ["violence", "social_bias", "profanity"]

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

        # The OpenAI client uses our custom httpx client. No instructor needed here.
        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE_URL,
            http_client=http_client
        )
        logging.info(f"LLM client configured for model '{LLM_MODEL_NAME}' at '{LLM_API_BASE_URL}'")

    def process(self, message: OuterWrapper) -> OuterWrapper:
        """
        Takes an OuterWrapper, checks it for various harms using an LLM,
        and returns the wrapper with any detected harms added to the error list.
        """
        try:
            logging.info(f"[{message.message_id}] - Starting LLM guardian processing.")

            for harm in HARMS_TO_CHECK:
                logging.debug(f"[{message.message_id}] - Checking for harm: {harm}")
                completion = self.client.chat.completions.create(
                    model=LLM_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": harm},
                        {"role": "user", "content": message.content},
                    ],
                    max_tokens=5, # We only need a single word response
                    temperature=0.0
                )
                response_text = completion.choices[0].message.content.strip().lower()
                logging.info(f"[{message.message_id}] - Guardian check for '{harm}' returned: '{response_text}'")

                if 'yes' in response_text:
                    error_msg = f"guardian:detected:{harm}"
                    logging.warning(f"[{message.message_id}] - Harm detected! Appending error: {error_msg}")
                    message.error.append(error_msg)

        except Exception as e:
            error_msg = f"Guardian LLM call failed: {e}"
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
    Receives an event, processes it through the guardian, and replies with a
    new event indicating whether it passed or needs review.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    try:
        incoming_payload = request.get_json()
        incoming_wrapper = OuterWrapper(**incoming_payload)
        logging.info(f"[{incoming_wrapper.message_id}] - Received event from Broker.")
        # Store the number of errors *before* processing
        original_error_count = len(incoming_wrapper.error)

    except (ValidationError, TypeError) as e:
        logging.error(f"Failed to parse incoming event payload: {e}")
        return jsonify({"error": "Bad request: payload does not match expected schema"}), 400

    processed_wrapper = processor.process(incoming_wrapper)

    # Check if the guardian added any new errors
    if len(processed_wrapper.error) > original_error_count:
        event_type = "com.example.triage.review.required"
        logging.warning(f"[{processed_wrapper.message_id}] - Guardian detected issues. Routing for review.")
    else:
        event_type = "com.example.triage.guardian.passed"
        logging.info(f"[{processed_wrapper.message_id}] - Guardian checks passed. Routing for structuring.")

    # Construct the CloudEvent headers for the HTTP response.
    response_headers = {
        "Ce-Specversion": "1.0",
        "Ce-Type": event_type,
        "Ce-Source": "/services/guardian-processor", # Updated source
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
