"""Mock Roblox Studio MCP server for E2E tests.
Speaks JSON-RPC 2.0 over stdio (MCP stdio transport)."""

import sys, json, time

TOOLS = [
    {"name": "execute_luau", "description": "Execute Luau code"},
    {"name": "screen_capture", "description": "Capture screenshot"},
    {"name": "script_read", "description": "Read a script"},
    {"name": "script_create", "description": "Create a script"},
    {"name": "multi_edit", "description": "Edit a script"},
    {"name": "inspect_instance", "description": "Inspect an instance"},
    {"name": "search_game_tree", "description": "Search game tree"},
    {"name": "list_roblox_studios", "description": "List studios"},
]

def handle(req):
    method = req.get("method", "")
    req_id = req.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-mcp", "version": "1.0"}
            }
        }
    elif method == "notifications/initialized":
        return None  # no response for notifications
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        params = req.get("params", {})
        name = params.get("name", "")

        if name == "screen_capture":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": "[mock screenshot captured]"},
                        {"type": "image", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==", "mimeType": "image/png"}
                    ]
                }
            }
        elif name in {t["name"] for t in TOOLS}:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"[mock {name} ok]"}]
                }
            }
        else:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{name}' not found"}
            }
    elif req_id is not None:
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    return None


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"[mock error] {e}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()
