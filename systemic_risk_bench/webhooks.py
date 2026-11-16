"""Loopback-only, signed result webhooks with idempotent receipt storage."""

import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.request import Request, urlopen


class ResultWebhook:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.secret = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.received = 0
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                if self.path != "/results":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1_000_000:
                    self.send_error(413)
                    return
                body = self.rfile.read(length)
                signature = hmac.new(owner.secret, body, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(signature, self.headers.get("X-SRB-Signature", "")):
                    self.send_error(401)
                    return
                try:
                    event = json.loads(body)
                    event_id = event["event_id"]
                    if not isinstance(event_id, str) or len(event_id) != 64 or any(
                        c not in "0123456789abcdef" for c in event_id
                    ):
                        raise ValueError("invalid event id")
                except (ValueError, KeyError, TypeError):
                    self.send_error(400)
                    return
                with owner.lock:
                    target = owner.directory / (event_id + ".json")
                    if not target.exists():
                        target.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
                        owner.received += 1
                self.send_response(202)
                self.end_headers()
                self.wfile.write(b"accepted")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/results"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def emit(self, event):
        body = json.dumps(event, sort_keys=True, allow_nan=False).encode()
        request = Request(self.url, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-SRB-Signature":
            hmac.new(self.secret, body, hashlib.sha256).hexdigest()})
        with urlopen(request, timeout=10) as response:
            if response.status != 202:
                raise RuntimeError("webhook delivery not accepted")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
