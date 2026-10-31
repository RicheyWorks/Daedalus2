"""Focused synthetic tests only; no production imports or Win32 construction."""
import ast
import builtins
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('candidate_owned_windows', ROOT / 'owned_window_minimize.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
START = '2026-10-19T05:45:23.2515787Z'
TITLE = 'DaedalusRealm - Unreal Editor'


def row(hwnd=1, **changes):
    value = dict(hwnd=hwnd, pid=42, thread_id=100, title=TITLE, **{'class': 'UnrealWindow'},
                 visible=True, iconic=False, enabled=True, owner_hwnd=0, owner_pid=0, owner_enabled=None)
    value.update(changes)
    return value


class Fake:
    def __init__(self, rows, complete=True, accept=True):
        self.rows = copy.deepcopy(rows)
        self.complete, self.accept = complete, accept
        self.actions, self.snapshots = [], 0
        self.on_snapshot = lambda count: None
        self.now = 0

    def snapshot(self, pid):
        self.snapshots += 1
        self.on_snapshot(self.snapshots)
        return copy.deepcopy(self.rows)

    def window(self, hwnd, expected_pid=None):
        value = next((r for r in self.rows if r['hwnd'] == hwnd), None)
        if value is not None and expected_pid is not None and value['pid'] != expected_pid:
            raise m.WindowHold('window changed PID before owned metadata read')
        return copy.deepcopy(value)

    def minimize(self, hwnd):
        self.actions.append(('minimize', hwnd, 7))
        if self.complete and self.accept:
            next(r for r in self.rows if r['hwnd'] == hwnd)['iconic'] = True
        return self.accept

    def sleep(self, duration):
        self.now += duration


class SnapshotOS(Fake):
    """Fake user32 metadata driving the ACTUAL adapter snapshot, never Win32."""
    def __init__(self, rows):
        super().__init__(rows)
        self.metadata_reads = []
        self.before_pid = lambda hwnd, count: None
        self.pid_calls = {}
        class DWORD:
            value = 0
        self.native = object.__new__(m.Win32Adapter)
        self.native.c = SimpleNamespace(WINFUNCTYPE=lambda *args: lambda fn: fn, byref=lambda value: value)
        self.native.w = SimpleNamespace(BOOL=bool, HWND=int, LPARAM=int, DWORD=DWORD)
        def lookup(hwnd):
            return next((r for r in self.rows if r['hwnd'] == hwnd), None)
        def process(hwnd, out):
            self.pid_calls[hwnd] = self.pid_calls.get(hwnd, 0) + 1
            self.before_pid(hwnd, self.pid_calls[hwnd])
            value = lookup(hwnd)
            if value is None: return 0
            out.value = value['pid']
            self.metadata_reads.append(('pid', hwnd))
            return value['thread_id']
        def enum_windows(callback, unused):
            for hwnd in [r['hwnd'] for r in self.rows]:
                if not callback(hwnd, 0): return False
            return True
        def own_window(hwnd, expected_pid=None):
            value = lookup(hwnd)
            if value is None: return None
            if value['pid'] != 42 or (expected_pid is not None and value['pid'] != expected_pid):
                raise AssertionError('foreign title/class read')
            self.metadata_reads.append(('owned_full', hwnd))
            return copy.deepcopy(value)
        self.native.user = SimpleNamespace(IsWindow=lambda hwnd: lookup(hwnd) is not None,
            GetWindowThreadProcessId=process,
            IsWindowVisible=lambda hwnd: lookup(hwnd)['visible'],
            GetWindow=lambda hwnd, code: lookup(hwnd)['owner_hwnd'], EnumWindows=enum_windows)
        self.native.window = own_window

    def snapshot(self, pid):
        self.snapshots += 1
        self.on_snapshot(self.snapshots)
        return self.native.snapshot(pid)


class OwnedWindowsTests(unittest.TestCase):
    def run_checkpoint(self, adapter, identity=None):
        return m.minimize_owned(adapter, 42, START, TITLE,
            identity or (lambda: {'pid': 42, 'start_utc': START}),
            timeout=.2, interval=.05, clock=lambda: adapter.now, sleep=adapter.sleep)

    def test_import_is_inert_and_does_not_load_win32(self):
        original = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name == 'ctypes' or name.startswith('ctypes.'):
                self.fail('Win32 dependency imported during inert module load')
            return original(name, *args, **kwargs)
        with mock.patch('builtins.__import__', side_effect=guarded):
            scope = {'__name__': 'inert_source_check'}
            exec(compile((ROOT / 'owned_window_minimize.py').read_text(), 'helper', 'exec'), scope)

    def test_late_message_log_after_main_hidden(self):
        f = Fake([row(visible=False), row(2, title='Message Log', owner_hwnd=1, owner_pid=42, owner_enabled=True)])
        result = self.run_checkpoint(f)
        self.assertEqual(result['status'], 'MINIMIZED_OR_HIDDEN')
        self.assertEqual(f.actions, [('minimize', 2, 7)])
        self.assertFalse(result['after'][0]['visible'])

    def test_both_visible_known_windows_minimize_without_other_actions(self):
        f = Fake([row(), row(2, title='Message Log', owner_hwnd=1, owner_pid=42, owner_enabled=True)])
        self.run_checkpoint(f)
        self.assertEqual(f.actions, [('minimize', 1, 7), ('minimize', 2, 7)])

    def test_already_iconic_is_noop(self):
        f = Fake([row(iconic=True)])
        self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_hidden_windows_are_never_shown(self):
        f = Fake([row(visible=False), row(2, title='Message Log', visible=False)])
        self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_owner_minimize_hides_secondary_and_never_reshows_it(self):
        f = Fake([row(), row(2, title='Message Log', owner_hwnd=1, owner_pid=42, owner_enabled=True)])
        minimize = f.minimize
        def hide_owned(hwnd):
            result = minimize(hwnd)
            if hwnd == 1: f.rows[1]['visible'] = False
            return result
        f.minimize = hide_owned
        self.run_checkpoint(f)
        self.assertEqual(f.actions, [('minimize', 1, 7)])

    def test_foreign_pid_refuses_before_action(self):
        f = Fake([row(), row(2, pid=99, title='Message Log')])
        with self.assertRaises(m.WindowHold): self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_actual_snapshot_foreign_owned_direct_and_chained_hold(self):
        # R1 filtered both foreign rows out and would minimize the main window.
        old_scope = {'__name__': 'frozen_r1_snapshot_oracle'}
        exec(compile((ROOT / 'fixtures' / 'owned_window_minimize_r1.py').read_text(),
                     'frozen-r1-helper', 'exec'), old_scope)
        for chain in (False, True):
            values = [row(), row(9, pid=99, title='MUST NOT READ', owner_hwnd=8 if chain else 1)]
            if chain: values.append(row(8, pid=98, title='MUST NOT READ', visible=False, owner_hwnd=1))
            f = SnapshotOS(values)
            with self.assertRaisesRegex(m.WindowHold, 'visible foreign window owned by target'):
                self.run_checkpoint(f)
            self.assertEqual(f.actions, [])
            self.assertEqual([x for x in f.metadata_reads if x[0] == 'owned_full'], [('owned_full', 1)])
            old = SnapshotOS(values)
            old.native.snapshot = old_scope['Win32Adapter'].snapshot.__get__(old.native)
            self.run_checkpoint(old)
            self.assertEqual(old.actions, [('minimize', 1, 7)])

    def test_actual_snapshot_unrelated_and_hidden_foreign_ignored(self):
        f = SnapshotOS([row(), row(9, pid=99, title='MUST NOT READ'),
            row(8, pid=98, title='MUST NOT READ', visible=False, owner_hwnd=1)])
        result = self.run_checkpoint(f)
        self.assertEqual(result['status'], 'MINIMIZED_OR_HIDDEN')
        self.assertEqual(f.actions, [('minimize', 1, 7)])
        self.assertFalse(any(kind == 'owned_full' and hwnd != 1 for kind, hwnd in f.metadata_reads))

    def test_actual_snapshot_disappearing_and_reused_owner_hold(self):
        for mutation in ('disappear', 'reuse', 'reassociate'):
            f = SnapshotOS([row(), row(9, pid=99, owner_hwnd=8), row(8, pid=98, visible=False)])
            def change(hwnd, count):
                # Owner 8 is queried once by enumeration, then by the chain;
                # mutate at chain revalidation to detect the changed identity.
                if hwnd == 8 and count == 3:
                    if mutation == 'disappear': f.rows[:] = [r for r in f.rows if r['hwnd'] != 8]
                    elif mutation == 'reuse': next(r for r in f.rows if r['hwnd'] == 8)['thread_id'] += 1
                    else: next(r for r in f.rows if r['hwnd'] == 8)['owner_hwnd'] = 1
            f.before_pid = change
            with self.assertRaises(m.WindowHold): self.run_checkpoint(f)
            self.assertEqual(f.actions, [])

    def test_actual_snapshot_cycle_and_bounded_chain_hold(self):
        cycle = [row(), row(9, pid=99, owner_hwnd=8), row(8, pid=98, visible=False, owner_hwnd=9)]
        deep = [row()] + [row(n, pid=99, visible=n == 10, owner_hwnd=n + 1 if n < 27 else 0) for n in range(10, 28)]
        for values in (cycle, deep):
            f = SnapshotOS(values)
            with self.assertRaisesRegex(m.WindowHold, 'owner-chain (cycle|limit)'):
                self.run_checkpoint(f)
            self.assertEqual(f.actions, [])

    def test_actual_snapshot_late_foreign_owned_before_action_holds(self):
        f = SnapshotOS([row()])
        def late(count):
            if count == 2: f.rows.append(row(9, pid=99, owner_hwnd=1))
        f.on_snapshot = late
        with self.assertRaisesRegex(m.WindowHold, 'visible foreign window owned by target'):
            self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_actual_window_reused_foreign_pid_before_text_on_both_revalidations(self):
        # Exercise the real window() method with fake user32, not SnapshotOS's
        # full-row mock. Neither a buffer allocation nor a text/class API is
        # reachable once GetWindowThreadProcessId reports a foreign PID.
        for phase in ('before_action', 'postcondition_poll'):
            with self.subTest(phase=phase):
                native = object.__new__(m.Win32Adapter)
                native.c = SimpleNamespace(byref=lambda value: value,
                    create_unicode_buffer=mock.Mock(side_effect=AssertionError('foreign text buffer')))
                native.w = SimpleNamespace(DWORD=lambda: SimpleNamespace(value=0))
                def process(hwnd, out):
                    out.value = 99
                    return 101
                native.user = SimpleNamespace(IsWindow=lambda hwnd: True,
                    GetWindowThreadProcessId=process, GetWindowTextW=mock.Mock(),
                    GetClassNameW=mock.Mock())
                f = Fake([row()])
                calls = []
                def revalidate(hwnd, expected_pid=None):
                    calls.append(expected_pid)
                    self.assertEqual(expected_pid, 42)
                    if phase == 'postcondition_poll' and len(calls) == 1:
                        return row()
                    return native.window(hwnd, expected_pid=expected_pid)
                f.window = revalidate
                with self.assertRaisesRegex(m.WindowHold, 'PID before owned metadata'):
                    self.run_checkpoint(f)
                self.assertEqual(len(calls), 1 if phase == 'before_action' else 2)
                self.assertEqual(f.actions, [] if phase == 'before_action' else [('minimize', 1, 7)])
                native.c.create_unicode_buffer.assert_not_called()
                native.user.GetWindowTextW.assert_not_called()
                native.user.GetClassNameW.assert_not_called()

    def test_unknown_visible_or_dialog_refuses_before_action(self):
        for changes in ({'title': 'Unapproved Tool'}, {'title': 'Confirm', 'class': '#32770'}):
            with self.subTest(changes=changes):
                f = Fake([row(), row(2, **changes)])
                with self.assertRaises(m.WindowHold): self.run_checkpoint(f)
                self.assertEqual(f.actions, [])

    def test_disabled_main_or_owner_refuses_before_action(self):
        for rows in ([row(enabled=False)], [row(), row(2, title='Message Log', owner_hwnd=1, owner_pid=42, owner_enabled=False)]):
            f = Fake(rows)
            with self.assertRaises(m.WindowHold): self.run_checkpoint(f)
            self.assertEqual(f.actions, [])

    def test_reused_handle_thread_is_revalidated_before_action(self):
        f = Fake([row()])
        def change(count):
            if count == 2: f.rows[0]['thread_id'] = 101
        f.on_snapshot = change
        with self.assertRaisesRegex(m.WindowHold, 'identity changed'): self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_missing_stale_and_changed_process_start_refuse(self):
        for identity in ({'pid': 99, 'start_utc': START}, {'pid': 42, 'start_utc': START.replace('7Z', '8Z')}, {'pid': 42}):
            f = Fake([row()])
            with self.assertRaises(m.WindowHold): self.run_checkpoint(f, lambda: identity)
            self.assertEqual(f.actions, [])
        f = Fake([row()]); calls = []
        def change_identity():
            calls.append(1)
            return {'pid': 42, 'start_utc': START if len(calls) == 1 else START.replace('7Z', '8Z')}
        with self.assertRaises(m.WindowHold): self.run_checkpoint(f, change_identity)
        self.assertEqual(f.actions, [])

    def test_exact_seven_digit_utc_identity(self):
        self.assertEqual(m.start_token(START), START)
        self.assertEqual(m.start_token('2026-10-19T05:45:23.2515787+00:00'), START)
        self.assertNotEqual(m.start_token('2026-10-19T05:45:23.251578Z'), START)

    def test_failed_request_or_postcondition_is_hold_not_success(self):
        for complete, accept in ((False, True), (True, False)):
            f = Fake([row()], complete=complete, accept=accept)
            with self.assertRaises(m.WindowHold): self.run_checkpoint(f)
            self.assertEqual(f.actions, [('minimize', 1, 7)])
            self.assertLessEqual(f.now, .25)

    def test_new_window_at_final_checkpoint_refuses_readiness(self):
        f = Fake([row(iconic=True)])
        def late(count):
            if count == 2: f.rows.append(row(2, title='Message Log'))
        f.on_snapshot = late
        with self.assertRaisesRegex(m.WindowHold, 'readiness refused'): self.run_checkpoint(f)
        self.assertEqual(f.actions, [])

    def test_no_close_activate_or_restore_surface(self):
        tree = ast.parse((ROOT / 'owned_window_minimize.py').read_text())
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertFalse(names & {'CloseWindow', 'CloseMainWindow', 'PostMessageW', 'SetForegroundWindow', 'SetFocus', 'BringWindowToTop'})
        self.assertEqual(m.SW_SHOWMINNOACTIVE, 7)

    def test_lifecycle_hold_cannot_report_ready_or_release(self):
        # Execute ONLY the check function AST with injected mocks, never import
        # the production lifecycle/benchmark, subprocess, ctypes or OS adapter.
        tree = ast.parse((ROOT / 'fixtures' / 'official_mcp_blueprint_lifecycle_check.py.txt').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check')
        receipts = []
        def require(ok, reason):
            if not ok: raise RuntimeError(reason)
        scope = dict(guard=lambda: None, load=lambda name: {'pid': 42, 'main': True, 'start_utc': START},
            state=lambda: {'editors': [{'Id': 42, 'Responding': True}], 'listeners': [{'LocalPort': 9877, 'OwningProcess': 42, 'LocalAddress': '127.0.0.1'}]},
            windows=lambda pid: [row()], b=SimpleNamespace(require=require, utc=lambda: 'synthetic'),
            _window_start=lambda *args: START, write=lambda name, value: receipts.append(copy.deepcopy(value)),
            json=json, time=SimpleNamespace(time_ns=lambda: 1), print=lambda *args: None)
        for reason in ('unknown visible window', 'IsIconic postcondition timed out'):
            receipts.clear()
            def hold(*args): raise m.WindowHold(reason)
            scope['_minimize_checkpoint'] = hold
            exec(compile(ast.Module(body=[node], type_ignores=[]), 'check-only', 'exec'), scope)
            with self.assertRaisesRegex(RuntimeError, 'no readiness'): scope['check']('launch')
            self.assertEqual(receipts[-1]['stage'], 'OWNED_WINDOW_MINIMIZE_HOLD')


if __name__ == '__main__':
    unittest.main(verbosity=2)
