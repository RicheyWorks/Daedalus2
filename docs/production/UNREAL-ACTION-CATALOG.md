# Saved Unreal action catalog

Use the existing owner's MCP client to obtain toolset descriptions during an agreed read-only window. This consumer makes no server calls. Store descriptions in this artifact wrapper (not a new server protocol):

```json
{"schema_version":1,"toolsets":{"EditorToolset.EditorAppToolset":{"tools":[{"name":"EditorToolset.EditorAppToolset.IsPIERunning","inputSchema":{"type":"object"}}]}}}
```

Run `python tools/unreal_mcp/action_catalog.py --capture descriptions.json --out actions.json`.

The catalog counts unique toolset/name pairs, preserves schemas, descriptions and declared annotations, and initializes every execution state to not-executed. Names such as Get/Inspect do not imply a read-only effect; absent annotations remain unknown. Metadata does not authorize actions. Existing outputs are refused.

This gives the future benchmark/workbook a concrete discovered-action denominator. It does not enumerate every Unreal function, prove an action was executed, or prove all toolsets were captured. Capture provenance and runtime execution evidence must be retained separately. No live catalog collection occurred in this source change.
