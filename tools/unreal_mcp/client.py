# SPDX-License-Identifier: MIT
"""Epic Unreal MCP client (UE 5.8 ModelContextProtocol plugin, Streamable HTTP on 127.0.0.1:8000).

Verified 2026-10-14 00:42 on DaedalusRealm: initialize -> Mcp-Session-Id; meta-tools list_toolsets /
describe_toolset(toolset_name) / call_tool(toolset_name, tool_name=<short name>, arguments).

    python tools/unreal_mcp/client.py toolsets
    python tools/unreal_mcp/client.py describe EditorToolset.EditorAppToolset
    python tools/unreal_mcp/client.py call EditorToolset.EditorAppToolset IsPIERunning '{}'
    python tools/unreal_mcp/client.py ready        # exit 0 iff the server answers initialize
"""
import json
import sys
if __package__:
    from .transport import post_json
else:
    from transport import post_json

URL = "http://127.0.0.1:8000/mcp"


class Mcp:
    def __init__(self, url=URL, timeout=60):
        self.url, self.timeout, self.sid, self._id = url, timeout, None, 0
        self.last_transfer = {}
        r = self._post({"jsonrpc": "2.0", "id": self._next(), "method": "initialize",
                        "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "daedalus", "version": "1"}}})
        self.server = r.get("result", {})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _next(self):
        self._id += 1
        return self._id

    def _post(self, body):
        session = {"id": self.sid}
        self.last_transfer = {}
        try:
            return post_json(self.url, body, session, timeout=self.timeout,
                             observation=self.last_transfer) or {}
        finally:
            self.sid = session["id"]

    def tools(self):
        return self._post({"jsonrpc": "2.0", "id": self._next(), "method": "tools/list", "params": {}})["result"]["tools"]

    def meta(self, name, **args):
        r = self._post({"jsonrpc": "2.0", "id": self._next(), "method": "tools/call", "params": {"name": name, "arguments": args}})
        if "error" in r:
            raise RuntimeError(r["error"])
        res = r["result"]
        text = "".join(c.get("text", "") for c in res.get("content", []))
        if res.get("isError"):
            raise RuntimeError(text)
        try:
            return json.loads(text)
        except ValueError:
            return text

    def toolsets(self):
        return self.meta("list_toolsets")

    def describe(self, toolset):
        return self.meta("describe_toolset", toolset_name=toolset)

    def call(self, toolset, tool, **args):
        """Native tool call; `tool` is the SHORT name (IsPIERunning, not EditorToolset.EditorAppToolset.IsPIERunning)."""
        out = self.meta("call_tool", toolset_name=toolset, tool_name=tool, arguments=args)
        return out.get("returnValue", out) if isinstance(out, dict) else out


def ready(url=URL):
    try:
        return bool(Mcp(url, timeout=5).server)
    except Exception:
        return False


def main(argv):
    if not argv or argv[0] == "ready":
        ok = ready()
        print("mcp ready" if ok else "mcp not listening on " + URL)
        return 0 if ok else 1
    m = Mcp()
    if argv[0] == "toolsets":
        print(m.toolsets())
    elif argv[0] == "describe":
        d = m.describe(argv[1])
        for t in d.get("tools", []):
            print(t["name"].split(".")[-1], "-", t.get("description", "").splitlines()[0] if t.get("description") else "")
    elif argv[0] == "call":
        print(json.dumps(m.call(argv[1], argv[2], **(json.loads(argv[3]) if len(argv) > 3 else {})), indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
