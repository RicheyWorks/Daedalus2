# The bridge protocol

The Claude Unreal Bridge plugin listens on **127.0.0.1:9877** (or `CLAUDE_UNREAL_PORT`) inside the Unreal
Editor. Any program can drive it; MCP is not required.

## A call

1. Open a TCP connection.
2. Send one line of JSON:
   ```json
   {"id": 1, "type": "execute_python", "params": {"code": "result = 6 * 7"}}
   ```
3. Read one line of JSON back:
   ```json
   {"id": 1, "status": "ok", "result": {"stdout": "", "result": 42}}
   ```
   or, on failure:
   ```json
   {"id": 1, "status": "error", "message": "ValueError: ...", "traceback": "..."}
   ```
4. The bridge then closes the connection. Use one connection per call.

`params.bridge_timeout` (seconds, default 1800) caps how long the bridge waits for the editor to run the
command.

## Commands

`list_commands` returns every command with its description and parameters, including commands a project
registered.

| Command | Params | Result |
|---|---|---|
| `ping` | | `engine`, `project`, `level`, `actors`, `playing`, `bridge_port` |
| `list_commands` | | `commands: [{name, description, params}]` |
| `get_level_info` | `limit`, `folder` | `level`, `actors_total`, `actors: [{label, class, folder, location}]`, `selected` |
| `get_actor_info` | `name` | `label`, `class`, `folder`, `location`, `rotation`, `scale`, `bounds`, `components` |
| `execute_python` | `code` | `stdout` and `result` (whatever the code assigned to `result`) |
| `viewport_screenshot` | `width`, `height` | `image_png_base64`, `path`, `bytes` |
| `play` / `stop` | `simulate` (play) | `playing` |
| `save` | | `level_saved`, `dirty_packages_saved` |
| `output_log` | `lines`, `filter` | `file`, `lines` |

Locations are in Unreal units (cm) with Z up. Rotations are `[pitch, yaw, roll]` in degrees.

## How commands run

- Every command runs on the editor's game thread. Socket threads only queue work, and a Slate post-tick
  callback runs it.
- A command can be a Python generator. It is then stepped once per editor tick until it returns, so it can
  wait for the editor (a screenshot being written, Play starting) without freezing it.

## Adding commands from your project

```python
import claude_unreal_bridge as bridge

def import_world(params):
    ...                      # plain function, or a generator that yields once per tick
    return {"ok": True}

bridge.register("myproject.import_world", import_world, "Import a world", {"server": "str"})
```

Use `project.verb` names. Put the call in your plugin's `init_unreal.py`. If your plugin can load before
this one, import inside a slate tick callback.

## Dialogs

A modal dialog blocks the game thread, so bridge calls time out until the dialog is answered. The MCP
extension's `editor_windows` and `window_input` tools (`extension/server/win.ps1`) work outside the editor
and can answer it: they list Unreal windows with pictures, then click or press keys in one. Any agent on
Windows can run `win.ps1` directly:

```
powershell -NoProfile -ExecutionPolicy Bypass -File win.ps1 -Op list
powershell -NoProfile -ExecutionPolicy Bypass -File win.ps1 -Op input -Hwnd 123456 -Keys enter
```

## Security

The bridge runs whatever `execute_python` is sent, with your user's permissions. It serves only 127.0.0.1,
so other machines can't reach it, but any program on the same computer can while the editor is open. Set
`CLAUDE_UNREAL_BRIDGE=off` to keep it from starting.
