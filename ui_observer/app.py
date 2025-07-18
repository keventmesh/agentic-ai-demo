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

# --- In-Memory Message Announcer for SSE (Replaces Flask-SSE/Redis) ---
# This class handles broadcasting messages to all connected UI clients.
class MessageAnnouncer:
    def __init__(self):
        self.listeners = []
        self.history = collections.deque(maxlen=50)

    def listen(self):
        for msg in list(self.history):
            yield msg
        q = queue.Queue(maxsize=10)
        self.listeners.append(q)
        try:
            while True:
                msg = q.get()
                yield msg
        finally:
            self.listeners.remove(q)

    def announce(self, msg):
        self.history.append(msg)
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]

announcer = MessageAnnouncer()

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK", 200

@app.route('/stream')
def stream():
    return Response(announcer.listen(), mimetype='text/event-stream')

@app.route('/', methods=['POST'])
def handle_event():
    """
    Receives CloudEvents from the Broker and announces them to UI clients.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 415

    cloud_event = {
        "type": request.headers.get('Ce-Type', 'unknown-type'),
        "source": request.headers.get('Ce-Source', 'unknown-source'),
        "id": request.headers.get('Ce-Id', 'unknown-id'),
        "specversion": request.headers.get('Ce-Specversion', 'unknown'),
        "payload": request.get_json()
    }

    # The messageId for correlation is still the subject
    message_id = request.headers.get('Ce-Subject', 'unknown-subject')

    # Create a structured message for the frontend
    sse_data = {
        "messageId": message_id,
        "cloudEvent": cloud_event
    }

    sse_msg = f"event: triage_event\ndata: {json.dumps(sse_data)}\n\n"

    announcer.announce(sse_msg)
    logging.info(f"Relayed event '{cloud_event['type']}' from '{cloud_event['source']}' for message '{message_id}' to UI.")

    return jsonify({"status": "event relayed to UI"}), 200

if __name__ == '__main__':
    logging.info(f"UI Observer service starting on port {APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True, threaded=True)
