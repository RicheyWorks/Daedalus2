"""Bounded owned-window checkpoint; import is inert and Win32 is lazy.

The caller supplies its existing PID/start-time observation. This is not a
background watcher. Unknown visible windows or possible modal state are HOLD.
"""
import re
import time

SW_SHOWMINNOACTIVE = 7
_IDENTITY = ('hwnd', 'pid', 'thread_id', 'title', 'class', 'owner_hwnd', 'owner_pid')


class WindowHold(RuntimeError):
    def __init__(self, reason, evidence=None):
        super().__init__(reason)
        self.evidence = evidence or {}


def start_token(value):
    """Preserve FILETIME's seven fractional digits; accept UTC spellings only."""
    if not isinstance(value, str):
        raise WindowHold('missing process start identity')
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(?:Z|\+00:00)', value)
    if not match:
        raise WindowHold('invalid UTC process start identity')
    return match[1] + '.' + (match[2] or '').ljust(7, '0') + 'Z'


def minimize_owned(adapter, pid, start_utc, main_title, identity, *,
                   timeout=2.0, interval=0.05, clock=time.monotonic, sleep=time.sleep):
    """Minimize only approved currently visible windows, then verify IsIconic.

    adapter supplies snapshot(pid), window(hwnd), minimize(hwnd). identity() is
    the caller's existing metadata observation, returning pid/start_utc. No
    close, focus, restore, show-hidden or minimize-all operation exists here.
    """
    if type(pid) is not int or pid <= 0 or not isinstance(main_title, str) or not main_title.endswith(' - Unreal Editor'):
        raise WindowHold('invalid owned process/main-title binding')
    expected_start = start_token(start_utc)
    if not (0 < timeout <= 5 and 0 < interval <= timeout):
        raise WindowHold('invalid bounded polling limits')
    evidence = {'pid': pid, 'start_utc': start_utc, 'main_title': main_title, 'actions': []}

    def owner_check():
        current = identity()
        if current.get('pid') != pid or start_token(current.get('start_utc')) != expected_start:
            raise WindowHold('process identity changed', evidence)

    def validate(rows):
        if len(rows) > 128 or len({r['hwnd'] for r in rows}) != len(rows):
            raise WindowHold('window inventory ambiguous/oversized', evidence)
        mains = [r for r in rows if r['pid'] == pid and r['class'] == 'UnrealWindow' and r['title'] == main_title]
        if len(mains) != 1:
            raise WindowHold('exact main window not unique', evidence)
        if not mains[0]['enabled']:
            raise WindowHold('main window disabled; possible modal dialog', evidence)
        if sum(r['visible'] and r['title'] == 'Message Log' for r in rows) > 1:
            raise WindowHold('secondary window title ambiguous', evidence)
        for row in rows:
            if row['pid'] != pid:
                raise WindowHold('foreign PID in owned inventory', evidence)
            if not row['visible']:
                continue
            if row['class'] != 'UnrealWindow' or row['title'] not in (main_title, 'Message Log'):
                raise WindowHold('unknown visible window; no action', evidence)
            if not row['enabled'] or (row['owner_hwnd'] and
                    (row['owner_pid'] != pid or row['owner_enabled'] is not True)):
                raise WindowHold('disabled/foreign owner; possible modal dialog', evidence)
        return rows

    def same_window(before, current):
        if current is None or any(before[k] != current[k] for k in _IDENTITY):
            raise WindowHold('window identity changed/reused', evidence)
        validate_current = dict(current)
        if not validate_current['enabled'] or (validate_current['owner_hwnd'] and
                (validate_current['owner_pid'] != pid or validate_current['owner_enabled'] is not True)):
            raise WindowHold('window/owner became disabled', evidence)
        return current

    owner_check()
    rows = validate(adapter.snapshot(pid))
    evidence['before'] = rows
    for row in rows:
        if not row['visible'] or row['iconic']:
            continue
        # Re-observe the entire inventory before acting on an owner: minimizing
        # an owner can hide owned windows, including an unexpected dialog.
        owner_check()
        validate(adapter.snapshot(pid))
        current = same_window(row, adapter.window(row['hwnd']))
        if not current['visible'] or current['iconic']:
            continue
        if not adapter.minimize(current['hwnd']):
            raise WindowHold('minimize request not accepted', evidence)
        evidence['actions'].append({'hwnd': current['hwnd'], 'command': SW_SHOWMINNOACTIVE})
        deadline = clock() + timeout
        while True:
            owner_check()
            observed = same_window(current, adapter.window(current['hwnd']))
            if observed['iconic']:
                break
            if clock() >= deadline:
                raise WindowHold('IsIconic postcondition timed out', evidence)
            sleep(interval)
    owner_check()
    after = validate(adapter.snapshot(pid))
    evidence['after'] = after
    if any(r['visible'] and not r['iconic'] for r in after):
        raise WindowHold('late/non-minimized visible window; readiness refused', evidence)
    evidence['status'] = 'MINIMIZED_OR_HIDDEN'
    return evidence


class Win32Adapter:
    """Construct only in the approved live lifecycle; never during mock tests."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.c, self.w = ctypes, wintypes
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        u = self.user
        u.IsWindow.argtypes = [wintypes.HWND]; u.IsWindow.restype = wintypes.BOOL
        u.IsWindowVisible.argtypes = [wintypes.HWND]; u.IsWindowVisible.restype = wintypes.BOOL
        u.IsIconic.argtypes = [wintypes.HWND]; u.IsIconic.restype = wintypes.BOOL
        u.IsWindowEnabled.argtypes = [wintypes.HWND]; u.IsWindowEnabled.restype = wintypes.BOOL
        u.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]; u.GetWindow.restype = wintypes.HWND
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.restype = ctypes.c_int
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.restype = ctypes.c_int
        u.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]; u.ShowWindowAsync.restype = wintypes.BOOL

    def window(self, hwnd):
        u, c, w = self.user, self.c, self.w
        if not u.IsWindow(hwnd):
            return None
        pid = w.DWORD(); thread = u.GetWindowThreadProcessId(hwnd, c.byref(pid))
        if not thread:
            raise WindowHold('window PID query failed')
        title, kind = c.create_unicode_buffer(1024), c.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, title, len(title))
        if not u.GetClassNameW(hwnd, kind, len(kind)):
            raise WindowHold('window class query failed')
        owner = int(u.GetWindow(hwnd, 4) or 0)
        owner_pid = w.DWORD()
        if owner and not u.GetWindowThreadProcessId(owner, c.byref(owner_pid)):
            raise WindowHold('owner PID query failed')
        return {'hwnd': int(hwnd), 'pid': pid.value, 'thread_id': thread,
                'title': title.value, 'class': kind.value,
                'visible': bool(u.IsWindowVisible(hwnd)), 'iconic': bool(u.IsIconic(hwnd)),
                'enabled': bool(u.IsWindowEnabled(hwnd)), 'owner_hwnd': owner,
                'owner_pid': owner_pid.value if owner else 0,
                'owner_enabled': bool(u.IsWindowEnabled(owner)) if owner else None}

    def snapshot(self, pid):
        c, w, u = self.c, self.w, self.user
        rows, errors = [], []
        callback_type = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        @callback_type
        def visit(hwnd, unused):
            try:
                owner = w.DWORD()
                if not u.GetWindowThreadProcessId(hwnd, c.byref(owner)):
                    raise WindowHold('enumerated PID query failed')
                if owner.value == pid:
                    row = self.window(hwnd)
                    if row is None:
                        raise WindowHold('window disappeared during enumeration')
                    rows.append(row)
                return True
            except Exception as exc:
                errors.append(exc)
                return False
        u.EnumWindows.argtypes = [callback_type, w.LPARAM]; u.EnumWindows.restype = w.BOOL
        if not u.EnumWindows(visit, 0) or errors:
            raise WindowHold('window enumeration failed')
        return rows

    def minimize(self, hwnd):
        return bool(self.user.ShowWindowAsync(hwnd, SW_SHOWMINNOACTIVE))
