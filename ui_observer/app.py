import os
import json
import logging
import queue
from flask import Flask, request, jsonify, render_template, Response

# --- Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
APP_PORT = int(os.getenv("PORT", "8080"))

# --- In-Memory Message Announcer for SSE (Replaces Flask-SSE/Redis) ---
# This class handles broadcasting messages to all connected UI clients.
class MessageAnnouncer:
    def __init__(self):
        self.listeners = []

    def listen(self):
        """
        Creates a new message queue for a client and yields messages from it.
        This is a generator function that will be used by the /stream route.
        """
        q = queue.Queue(maxsize=10) # A small buffer for messages
        self.listeners.append(q)
        try:
            while True:
                # Get a message from the queue, blocking until one is available
                msg = q.get()
                yield msg
        finally:
            # When the client disconnects, remove their queue from the listeners
            self.listeners.remove(q)

    def announce(self, msg):
        """
        Pushes a new message to all listening clients' queues.
        """
        for i in reversed(range(len(self.listeners))):
            try:
                # Put the message in the client's queue.
                # The 'block=False' will raise an exception if the queue is full,
                # preventing this handler from blocking.
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                # If a client's queue is full, we can assume they are lagging
                # and might have disconnected. We can safely ignore them.
                del self.listeners[i]

announcer = MessageAnnouncer()

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main UI page."""
    return render_template('index.html')

@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/stream')
def stream():
    """The SSE stream endpoint. Connects a client to the message announcer."""
    return Response(announcer.listen(), mimetype='text/event-stream')

@app.route('/', methods=['POST'])
def handle_event():
    """
    Receives CloudEvents from the Broker and announces them to UI clients.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    # Extract required CloudEvent attributes
    event_type = request.headers.get('Ce-Type', 'unknown-type')
    message_id = request.headers.get('Ce-Subject', 'unknown-subject')
    payload = request.get_json()

    # Create a message dictionary for the frontend
    sse_data = {
        "eventType": event_type,
        "messageId": message_id,
        "payload": payload
    }

    # Format the message for the SSE protocol: "data: <json_string>\n\n"
    # The event name 'triage_event' is now embedded in the data.
    sse_msg = f"event: triage_event\ndata: {json.dumps(sse_data)}\n\n"

    # Announce the formatted message to all connected clients
    announcer.announce(sse_msg)
    logging.info(f"Relayed event '{event_type}' for message '{message_id}' to UI.")

    return jsonify({"status": "event relayed to UI"}), 200

if __name__ == '__main__':
    logging.info(f"UI Observer service starting on port {APP_PORT}")
    # For local testing, running with threaded=True helps manage SSE connections.
    # In production, Gunicorn with gevent handles this.
    app.run(host='0.0.0.0', port=APP_PORT, debug=True, threaded=True)
