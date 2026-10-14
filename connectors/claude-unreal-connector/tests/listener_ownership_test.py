# SPDX-License-Identifier: MIT
"""Listener policy and cleanup regressions, using fake Unreal and ephemeral loopback sockets.

Run: python connectors/claude-unreal-connector/tests/listener_ownership_test.py
No editor is loaded. Mock tests never open sockets; real tests use the production
listener factory directly, never start the bridge or execute editor commands.
"""
import contextlib
import socket
import sys
import time
import types
import unittest
from unittest.mock import Mock, patch

from bridge_lifecycle_test import DormantThread, Fixture, Listener


class RecordingSocket(Listener):
    def __init__(self, fail=None):
        super().__init__()
        self.events = []
        self.fail = fail

    def _record(self, method, *args):
        self.events.append((method, *args))
        if method == self.fail:
            raise OSError("%s boom" % method)

    def setsockopt(self, *args):
        self._record("setsockopt", *args)

    def bind(self, address):
        self._record("bind", address)
        super().bind(address)

    def listen(self, backlog):
        self._record("listen", backlog)

    def close(self):
        self._record("close")
        super().close()


@contextlib.contextmanager
def socket_surface(bridge, platform, candidate, exclusive=True):
    """Give either policy branch a portable fake socket module, including on Linux CI."""
    surface = types.SimpleNamespace(
        AF_INET=socket.AF_INET,
        SOCK_STREAM=socket.SOCK_STREAM,
        SOL_SOCKET=socket.SOL_SOCKET,
        SO_REUSEADDR=socket.SO_REUSEADDR,
        socket=Mock(return_value=candidate),
    )
    if exclusive:
        surface.SO_EXCLUSIVEADDRUSE = -101  # A sentinel, never applied to a real socket.
    with patch.object(bridge, "socket", surface), patch.object(bridge, "sys", types.SimpleNamespace(platform=platform)):
        yield surface


class ListenerPolicyTests(unittest.TestCase):
    def test_platform_option_is_set_before_loopback_bind_and_listen(self):
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform):
                bridge = Fixture().bridge
                candidate = RecordingSocket()
                state = dict(bridge._server)
                with socket_surface(bridge, platform, candidate) as surface:
                    self.assertIs(bridge._create_listener(0), candidate)
                    option = surface.SO_EXCLUSIVEADDRUSE if platform == "win32" else surface.SO_REUSEADDR
                    surface.socket.assert_called_once_with(surface.AF_INET, surface.SOCK_STREAM)
                    self.assertEqual(candidate.events, [
                        ("setsockopt", surface.SOL_SOCKET, option, 1),
                        ("bind", ("127.0.0.1", 0)),
                        ("listen", 8),
                    ])
                self.assertEqual(candidate.closed, 0)
                self.assertEqual(bridge._server, state, "the factory must not publish server state")

    def test_windows_missing_exclusive_option_fails_closed_without_reuse(self):
        bridge = Fixture().bridge
        candidate = RecordingSocket()
        state = dict(bridge._server)
        with socket_surface(bridge, "win32", candidate, exclusive=False):
            with self.assertRaisesRegex(RuntimeError, "exclusive.*unavailable"):
                bridge._create_listener(0)
        self.assertEqual(candidate.events, [("close",)])
        self.assertEqual(candidate.closed, 1)
        self.assertEqual(bridge._server, state)

    def test_option_bind_and_listen_failures_close_only_new_descriptor(self):
        for platform in ("win32", "linux"):
            for stage in ("setsockopt", "bind", "listen"):
                with self.subTest(platform=platform, stage=stage), Fixture() as f:
                    owner = f.listeners[0]
                    state = dict(f.bridge._server)
                    candidate = RecordingSocket(fail=stage)
                    with socket_surface(f.bridge, platform, candidate) as surface:
                        with self.assertRaisesRegex(OSError, "%s boom" % stage):
                            f.bridge._create_listener(0)
                        self.assertEqual(candidate.events[-1], ("close",))
                        self.assertEqual(candidate.closed, 1)
                        options = [event for event in candidate.events if event[0] == "setsockopt"]
                        option = surface.SO_EXCLUSIVEADDRUSE if platform == "win32" else surface.SO_REUSEADDR
                        self.assertEqual(options, [("setsockopt", surface.SOL_SOCKET, option, 1)],
                                         "a failed exclusive option must never fall back to reuse")
                        completed_stages = [event[0] for event in candidate.events]
                        expected = ["setsockopt", "bind", "listen"][:["setsockopt", "bind", "listen"].index(stage) + 1]
                        self.assertEqual(completed_stages, expected + ["close"])
                    self.assertEqual(f.bridge._server, state)
                    self.assertEqual(owner.closed, 0, "an unrelated owner must remain open")

    def test_idempotent_start_does_not_create_reconfigure_or_close_existing_owner(self):
        with Fixture() as f:
            owner = f.listeners[0]
            state = dict(f.bridge._server)
            with patch.object(f.bridge.socket, "socket", side_effect=AssertionError("new socket")), \
                    patch.object(owner, "setsockopt", side_effect=AssertionError("reconfigured")), \
                    patch.object(owner, "bind", side_effect=AssertionError("rebound")), \
                    patch.object(owner, "close", side_effect=AssertionError("closed")):
                self.assertEqual(f.bridge.start(1), state["port"])
            self.assertEqual(f.bridge._server, state)
            self.assertEqual(owner.closed, 0)


class ListenerStartupTests(unittest.TestCase):
    def test_each_startup_failure_cleans_candidate_and_permits_later_start(self):
        for stage in ("getsockname", "thread_constructor", "thread_start", "callback", "log"):
            with self.subTest(stage=stage), Fixture() as f:
                original = f.listeners[0]
                f.bridge.stop()
                stopped = dict(f.bridge._server)
                candidate = Listener()
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(f.bridge.socket, "socket", return_value=candidate))
                    failure = RuntimeError("%s boom" % stage)
                    if stage == "getsockname":
                        stack.enter_context(patch.object(candidate, "getsockname", side_effect=failure))
                    elif stage == "thread_constructor":
                        stack.enter_context(patch.object(f.bridge.threading, "Thread", side_effect=failure))
                    elif stage == "thread_start":
                        stack.enter_context(patch.object(DormantThread, "start", side_effect=failure))
                    elif stage == "callback":
                        stack.enter_context(patch.object(f.unreal, "register_slate_post_tick_callback", side_effect=failure))
                    else:
                        stack.enter_context(patch.object(f.unreal, "log", side_effect=failure))
                    with self.assertRaisesRegex(RuntimeError, "%s boom" % stage):
                        f.start()
                self.assertEqual(candidate.closed, 1)
                self.assertEqual(original.closed, 1, "cleanup must not close an earlier listener twice")
                self.assertEqual(f.bridge._server, stopped)
                self.assertTrue(f.bridge._jobs.empty())
                self.assertEqual(f.bridge._running, [])
                self.assertEqual(f.start(), 9877)
                self.assertEqual(f.listeners[-1].closed, 0)

    def test_bind_or_listen_failure_before_publication_preserves_stopped_state(self):
        for stage in ("bind", "listen"):
            with self.subTest(stage=stage), Fixture() as f:
                f.bridge.stop()
                stopped = dict(f.bridge._server)
                candidate = RecordingSocket(fail=stage)
                with patch.object(f.bridge.socket, "socket", return_value=candidate):
                    with self.assertRaisesRegex(OSError, "%s boom" % stage):
                        f.start()
                self.assertEqual(candidate.closed, 1)
                self.assertEqual(f.bridge._server, stopped)
                self.assertEqual(f.start(), 9877)

    def test_startup_control_interrupt_is_reraised_after_candidate_cleanup(self):
        for stage in ("getsockname", "thread_constructor", "log"):
            with self.subTest(stage=stage), Fixture() as f:
                original = f.listeners[0]
                f.bridge.stop()
                stopped = dict(f.bridge._server)
                candidate = Listener()
                interrupt = KeyboardInterrupt("%s interrupted" % stage)
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(f.bridge.socket, "socket", return_value=candidate))
                    if stage == "getsockname":
                        stack.enter_context(patch.object(candidate, "getsockname", side_effect=interrupt))
                    elif stage == "thread_constructor":
                        stack.enter_context(patch.object(f.bridge.threading, "Thread", side_effect=interrupt))
                    else:
                        stack.enter_context(patch.object(f.unreal, "log", side_effect=interrupt))
                    with self.assertRaises(KeyboardInterrupt) as raised:
                        f.start()
                self.assertIs(raised.exception, interrupt)
                self.assertEqual(candidate.closed, 1)
                self.assertEqual(original.closed, 1)
                self.assertEqual(f.bridge._server, stopped)
                self.assertEqual(f.start(), 9877)


class RealListenerTests(unittest.TestCase):
    TIMEOUT = 2.0

    def setUp(self):
        self.bridge = Fixture().bridge
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)

    def listener(self, port=0):
        listener = self.bridge._create_listener(port)
        self.stack.callback(listener.close)
        listener.settimeout(self.TIMEOUT)
        return listener

    def connect(self, listener):
        client = socket.create_connection(listener.getsockname(), timeout=self.TIMEOUT)
        self.stack.callback(client.close)
        accepted, _ = listener.accept()
        self.stack.callback(accepted.close)
        accepted.settimeout(self.TIMEOUT)
        return client, accepted

    def graceful_close(self, client, accepted):
        """Drain both directions before a later bind; never force a reset with SO_LINGER."""
        client.shutdown(socket.SHUT_WR)
        self.assertEqual(accepted.recv(1), b"", "all client bytes must already have been consumed")
        accepted.shutdown(socket.SHUT_WR)
        self.assertEqual(client.recv(1), b"", "all server bytes must already have been consumed")
        accepted.close()
        client.close()

    def receive(self, peer, size):
        deadline = time.monotonic() + self.TIMEOUT
        data = bytearray()
        while len(data) < size:
            remaining = deadline - time.monotonic()
            self.assertGreater(remaining, 0, "loopback exchange exceeded its deadline")
            peer.settimeout(remaining)
            chunk = peer.recv(size - len(data))
            self.assertTrue(chunk, "peer closed before the complete payload arrived")
            data.extend(chunk)
        peer.settimeout(self.TIMEOUT)
        return bytes(data)

    def exchange(self, client, accepted):
        client.sendall(b"request")
        self.assertEqual(self.receive(accepted, 7), b"request")
        accepted.sendall(b"response")
        self.assertEqual(self.receive(client, 8), b"response")

    def test_production_policy_rejects_default_and_reuse_contenders_owner_still_responds(self):
        owner = self.listener()
        address = owner.getsockname()
        self.assertEqual(address[0], "127.0.0.1")
        self.assertNotEqual(address[1], 0)
        option = socket.SO_EXCLUSIVEADDRUSE if sys.platform == "win32" else socket.SO_REUSEADDR
        self.assertEqual(owner.getsockopt(socket.SOL_SOCKET, option), 1)
        if sys.platform == "win32":
            self.assertEqual(owner.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0)
        for reuse in (False, True):
            with self.subTest(contender_reuse=reuse), socket.socket(socket.AF_INET, socket.SOCK_STREAM) as contender:
                if reuse:
                    contender.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                with self.assertRaises(OSError):
                    contender.bind(address)
            client, accepted = self.connect(owner)
            self.exchange(client, accepted)
            self.graceful_close(client, accepted)

    def test_restart_only_after_listener_and_both_accepted_peers_are_closed(self):
        owner = self.listener()
        address = owner.getsockname()
        client, accepted = self.connect(owner)
        owner.close()
        # Closing a listener does not end its accepted session. Do not claim or
        # test that a replacement can bind immediately while that session lives.
        self.exchange(client, accepted)
        self.graceful_close(client, accepted)
        deadline = time.monotonic() + self.TIMEOUT
        while True:
            try:
                replacement = self.listener(address[1])
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        self.assertEqual(replacement.getsockname(), address)
        client, accepted = self.connect(replacement)
        self.exchange(client, accepted)
        self.graceful_close(client, accepted)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("%d/%d" % (result.testsRun - len(result.failures) - len(result.errors), result.testsRun))
    raise SystemExit(0 if result.wasSuccessful() else 1)
