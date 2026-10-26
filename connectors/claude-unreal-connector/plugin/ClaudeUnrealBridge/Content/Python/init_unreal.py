# SPDX-License-Identifier: MIT
"""Unreal runs every enabled plugin's Content/Python/init_unreal.py when the editor starts. This one starts the
Claude Unreal Bridge on 127.0.0.1 (port 9877, or CLAUDE_UNREAL_PORT). Headless runs (commandlets) have no
editor to operate and skip it, and so does CLAUDE_UNREAL_BRIDGE=off."""
import os

import unreal


def _headless():
    check = getattr(unreal, "is_running_commandlet", None)
    return bool(check()) if check else False


if not _headless() and os.environ.get("CLAUDE_UNREAL_BRIDGE", "on").lower() != "off":
    try:
        import claude_unreal_bridge
        claude_unreal_bridge.start()
    except Exception as e:  # a port in use (a second editor) must not stop the editor opening
        unreal.log_warning("Claude Unreal Bridge did not start: %s" % e)
