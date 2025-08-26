import os
import json
import logging
import queue
import collections
from flask import Flask, request, jsonify, render_template, Response

# --- Configuration ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
APP_PORT = int(os.getenv("PORT", "8080"))

# --- In-Memory Message Announcer for SSE ---
# This class handles broadcasting messages to all connected UI clients.
class MessageAnnouncer:
    def __init__(self):
        self.listeners = []
        # Store a history of the last 50 messages for clients that connect later
        self.history = collections.deque(maxlen=50)

    def listen(self):
        """Yields historical and then new messages for an SSE stream."""
        # First, send the history
        for msg in list(self.history):
            yield msg

        # Then, listen for new messages
        q = queue.Queue(maxsize=10)
        self.listeners.append(q)
        try:
            while True:
                msg = q.get()
                yield msg
        finally:
            self.listeners.remove(q)

    def announce(self, msg):
        """Adds a message to history and sends to all listeners."""
        self.history.append(msg)
        # Iterate backwards to safely remove listeners if queue is full
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

announcer = MessageAnnouncer()

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main inbox UI."""
    return render_template('inbox.html')

@app.route('/healthz', methods=['GET'])
def healthz():
    """Simple health check for Kubernetes probes."""
    return "OK", 200

@app.route('/stream')
def stream():
    """The SSE stream endpoint for the UI."""
    return Response(announcer.listen(), mimetype='text/event-stream')

@app.route('/', methods=['POST'])
def handle_event():
    """
    Receives CloudEvents from the Broker and announces them to UI clients.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    # Extract the relevant parts of the event
    event_type = request.headers.get('Ce-Type', 'unknown-type')
    message_id = request.headers.get('Ce-Subject', 'unknown-subject')
    payload = request.get_json()

    # The data for the frontend is the event's payload itself
    sse_data = payload

    # Format the message for Server-Sent Events (SSE)
    # The 'event:' line allows the frontend to have a specific listener
    sse_msg = f"event: finance_message\ndata: {json.dumps(sse_data)}\n\n"

    # Announce the message to all connected clients
    announcer.announce(sse_msg)
    logging.info(f"Relayed finance message '{message_id}' (type: {event_type}) to UI.")

    # Acknowledge receipt of the event
    return jsonify({"status": "event relayed to UI"}), 200

if __name__ == '__main__':
    logging.info(f"Finance Responder service starting on port {APP_PORT}")
    # Use threaded=True for handling multiple SSE clients
    app.run(host='0.0.0.0', port=APP_PORT, debug=True, threaded=True)
