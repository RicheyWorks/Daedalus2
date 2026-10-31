# SPDX-License-Identifier: MIT
"""Bounded, loopback-only static hosting for built demo validation.

Only explicitly mounted directories are served. Receipts describe server writes;
client body hashes and browser readiness must be checked separately.
"""
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
from pathlib import Path
import threading
import time
from urllib.parse import unquote, urlsplit


class DemoHTTP:
    def __init__(self, mounts, *, max_asset_bytes=16 * 1024 * 1024, timeout=10):
        self.mounts = {name: Path(root).resolve(strict=True) for name, root in mounts.items()}
        if not self.mounts or any(not name.isascii() or not name.isalnum()
                                  or not root.is_dir() for name, root in self.mounts.items()):
            raise ValueError("Mounts must be named directories")
        if not 0 < max_asset_bytes <= 64 * 1024 * 1024 or not 0 < timeout <= 30:
            raise ValueError("Asset size and timeout must be bounded")
        self.max_asset_bytes, self.timeout = max_asset_bytes, timeout
        self.receipts = []
        self._lock = threading.Lock()
        self.server = self.thread = None

    def resolve(self, url):
        decoded = unquote(urlsplit(url).path)
        parts = decoded.lstrip("/").split("/")
        if "\\" in decoded or "\0" in decoded or any(p in (".", "..") for p in parts):
            return None
        root = self.mounts.get(parts[0])
        if root is None:
            return None
        path = root.joinpath(*parts[1:]).resolve()
        return path if path.is_relative_to(root) and path.is_file() else None

    def __enter__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            # One response per connection makes failed/incomplete requests finite.
            protocol_version = "HTTP/1.0"

            def setup(self):
                super().setup()
                self.connection.settimeout(owner.timeout)

            def log_message(self, *args):
                pass

            def do_GET(self):
                self.serve(False)

            def do_HEAD(self):
                self.serve(True)

            def serve(self, head):
                started = time.monotonic()
                receipt = {"utc": datetime.now(timezone.utc).isoformat(),
                           "method": self.command, "path": urlsplit(self.path).path,
                           "status": None, "written_bytes": 0, "write_complete": False}
                try:
                    path = owner.resolve(self.path)
                    if path is None:
                        status, body, mime = 404, b"Not found\n", "text/plain"
                    else:
                        # A read cap still applies if the file changes after stat().
                        with path.open("rb") as source:
                            body = source.read(owner.max_asset_bytes + 1)
                        if len(body) > owner.max_asset_bytes:
                            status, body, mime = 413, b"Asset exceeds validation cap\n", "text/plain"
                        else:
                            status = 200
                            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                    receipt.update(status=status, body_bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), mime=mime)
                    self.send_response(status)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Connection", "close")
                    self.end_headers()
                    if not head:
                        for offset in range(0, len(body), 64 * 1024):
                            chunk = body[offset:offset + 64 * 1024]
                            self.wfile.write(chunk)
                            receipt["written_bytes"] += len(chunk)
                        self.wfile.flush()
                    receipt["write_complete"] = True
                except (OSError, ValueError) as error:
                    receipt["error"] = type(error).__name__ + ": " + str(error)
                    self.close_connection = True
                finally:
                    receipt["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
                    with owner._lock:
                        owner.receipts.append(receipt)

        class Server(ThreadingHTTPServer):
            request_queue_size = 32
            daemon_threads = True
            block_on_close = False

        self.server = Server(("127.0.0.1", 0), Handler)
        self.origin = "http://127.0.0.1:%d" % self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
