import os
import uuid
import logging
import requests
from flask import Flask, request, jsonify

# --- Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

APP_PORT = int(os.getenv("PORT", "8080"))

K_SINK = os.getenv('K_SINK')
if not K_SINK:
    logging.error("K_SINK environment variable not set. Cannot send events.")
    raise SystemExit("K_SINK environment variable not set.")

logging.info(f"Events will be sent to: {K_SINK}")
logging.info(f"Service is listening on port: {APP_PORT}")

# --- CloudEvent Creation ---
def create_cloudevent(content):
    """
    Creates a CloudEvent in the structured HTTP format.
    Generates a unique ID for the event and the message itself.
    """
    event_id = str(uuid.uuid4())
    # This ID serves as the unique identifier for the message throughout the system.
    message_id = event_id

    # The data payload is the OuterWrapper model's initial state
    payload = {
        "message_id": message_id,
        "content": content,
        "metadata": {},
        "structured": None,
        "route": None,
        "support": None,
        "website": None,
        "finance": None,
        "error": []
    }

    # The headers are the CloudEvent attributes
    headers = {
        "Ce-Specversion": "1.0",
        "Ce-Type": "com.example.triage.intake.new",
        "Ce-Source": "/services/file-intake-service",
        "Ce-Id": event_id,
        "Ce-Subject": message_id, # The subject of the event is the message ID
        "Content-Type": "application/json",
    }

    return headers, payload

# --- Flask Routes ---
@app.route('/healthz', methods=['GET'])
def healthz():
    """Simple health check endpoint for Kubernetes probes."""
    return "OK", 200

@app.route('/', methods=['POST'])
def handle_json_request():
    """
    Handles a JSON POST request, creates a CloudEvent, and sends it to the Broker.
    """
    if not request.is_json:
        logging.warning("Bad request: Mimetype is not application/json")
        return jsonify({"error": "Request must be application/json"}), 415

    data = request.get_json()

    if not data or "content" not in data:
        logging.warning("Bad request: Missing 'content' in JSON payload")
        return jsonify({"error": "JSON payload must include a 'content' key"}), 400

    content = data.get("content")

    if not isinstance(content, str) or not content:
        logging.warning("Bad request: 'content' must be a non-empty string")
        return jsonify({"error": "'content' must be a non-empty string"}), 400

    logging.info(f"Received message content, creating event.")
    headers, payload = create_cloudevent(content)

    try:
        logging.info(f"Sending event {headers['Ce-Id']} to Broker.")
        response = requests.post(K_SINK, json=payload, headers=headers, timeout=5.0)
        response.raise_for_status()

        logging.info(f"Event accepted by Broker with status code: {response.status_code}")
        return jsonify({"status": "event accepted", "eventId": headers['Ce-Id']}), 202

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send event to Broker: {e}")
        return jsonify({"error": "Failed to forward event to the eventing system"}), 503

    return jsonify({"error": "An unexpected error occurred"}), 500

# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
