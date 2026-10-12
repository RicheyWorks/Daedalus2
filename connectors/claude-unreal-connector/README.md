# Claude Unreal Connector

Lets Claude, or any agent, operate the open Unreal Editor:
- read the level
- run Python against the whole editor API
- screenshot the viewport
- play, stop and save
- answer dialogs, even when one has frozen the editor

It is built the same way as the [Claude Blender Connector](https://github.com/RicheyWorks/claude-blender-connector).

It has three parts, and each one can be used without the others:

| Part | What it is |
|---|---|
| `plugin/ClaudeUnrealBridge` | An Unreal plugin, Python only, so there is nothing to compile. It starts with the editor and listens on `127.0.0.1:9877`. Commands run on the editor's game thread. |
| `extension/` | A Claude desktop extension: an MCP server with no dependencies, packed as an `.mcpb`. It forwards Claude's tool calls to the bridge. It also carries a window harness (`server/win.ps1`) that sees and answers Unreal dialogs from outside the editor. |
| `clients/python/unreal_client.py` and `PROTOCOL.md` | For agents that don't speak MCP (Grok bots, scripts, CI): one JSON line over TCP per call. |

## Install (Windows)

Close the project in Unreal, then run this in PowerShell, with your own `.uproject` path:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/RicheyWorks/claude-unreal-connector/main/install.ps1))) -Project C:\Path\To\Game.uproject
```

It copies the plugin into the project, enables it (along with Python Editor Script Plugin and Editor
Scripting Utilities), and opens the Claude extension installer. Click **Install** there. When you open the
project in Unreal, the bridge starts. Add `-NoExtension` if you only want the plugin, for agents that use
the protocol directly.

## Tools (MCP)

| Tool | What it does |
|---|---|
| `unreal_status` | The engine version, project, open level, actor count, and whether Play is running |
| `get_level_info` / `get_actor_info` | Actors (filtered by Outliner folder), or one actor's transform, bounds, components, meshes and materials |
| `execute_python` | Python on the game thread with `unreal` imported (the whole editor API). Returns stdout and `result` |
| `viewport_screenshot` | The active viewport, as an image |
| `play` / `stop` | Play In Editor (or Simulate), waiting until it has started or ended |
| `save` | The level and every changed asset |
| `output_log` | The editor log, optionally filtered |
| `list_commands` / `run_command` | Commands your own project added to the bridge (see *Extending*) |
| `editor_windows` / `window_input` | Every Unreal window, dialogs included, with a picture of each; then click or press keys in one. Works while a dialog has frozen the editor. Windows only. |

Try asking Claude: *"In Unreal, add a sun and a sky to this level, frame the camera on the castle, and show
me a screenshot."*

## Extending: project commands

A project can add its own commands from its plugin's `init_unreal.py`:

```python
import claude_unreal_bridge as bridge
bridge.register("mygame.spawn_wave", spawn_wave, "Spawn the next enemy wave", {"size": "int"})
```

Claude finds them with `list_commands` and runs them with `run_command`. A command can be a generator that
yields once per editor tick, for work that has to wait for the editor. [Daedalus](https://github.com/RicheyWorks/Daedalus2)
registers `daedalus.import_world` and `daedalus.frame_world` this way.

## Development

The tests run the bridge against a stand-in `unreal` module, pumped like editor ticks, and drive the
extension over stdio the way Claude does. They cover:
- every tool
- add-on commands that run across several ticks
- a nested editor tick inside a command, the way `take_high_res_screenshot` causes one
- a frozen editor, which must give a clear timeout instead of hanging

```bash
python3 tests/host.py 9911 40 &
node tests/client.js 9911          # prints n/m last; exits 1 on any failure
```

The stand-in proves the plumbing. The real editor calls are proven in Unreal. The connector was developed
against UE 5.8.3 on Windows 11.

## Capability walk (`harness/caps/`)

This answers one question: what can an agent actually do in this editor? Each sweep and probe makes something
real, reads it back, and cleans up. The results go to `ledgers/capabilities.json`.

Live on UE 5.8.3:
- **Actor sweep:** every actor class. 266 of 332 spawn; 34 are abstract; 32 game-framework classes are excluded.
- **Factory sweep:** every asset factory. 161 make assets. 25 need a setting the UI normally asks for, and 78
  need a source file. 2 crash the engine (`LightWeightInstanceFactory`, `SlateWidgetStyleAssetFactory`).
- **Deep probes:** 17 of 17 pass. They cover:
  - material graphs and instance parameters
  - Blueprints with components and variables
  - structs, enums and DataTables
  - Sequencer keys and camera cuts
  - PCG graphs
  - Geometry Scripting to a static mesh
  - LODs and collision
  - Paper2D tilemaps
  - Enhanced Input
  - physics materials
  - Niagara, UMG and MetaSound assets
  - asset operations
  - glTF export and reimport

Anything that might crash runs in **the sandbox** (`sandbox.py`): a headless `UnrealEditor-Cmd` that the open
editor launches, under a supervisor. If it crashes, the supervisor reruns it and skips the item that crashed it,
which its progress file names. The user's editor is never at risk. The open editor can pull the harness straight
from GitHub:

```python
import urllib.request
RAW = "https://raw.githubusercontent.com/RicheyWorks/Daedalus2/main/connectors/claude-unreal-connector/harness/caps/"
ns = {}
exec(urllib.request.urlopen(RAW + "sandbox.py").read().decode(), ns)
result = ns["sandbox_supervise"](urllib.request.urlopen(RAW + "area_deep.py").read().decode(), "deep")
# later: result = ns["sandbox_poll"](out)
```

API traps found live:
- UE's Python spells `IDs` as `i_ds`.
- Asset creation from Geometry Scripting is in `GeometryScript_NewAssetUtils`.
- Editor subsystems are `None` in a commandlet.

## Security

`execute_python` runs whatever it is sent, with your user's permissions. The bridge serves only
`127.0.0.1`, so other machines can't reach it, but any program on your own computer can while the editor is
open. Set the environment variable `CLAUDE_UNREAL_BRIDGE=off` to keep it from starting.

## License

MIT
