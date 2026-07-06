"""
E2E test: Auto-launches a mock MCP server + bridge, then exercises the full WS protocol.

Tests:
  - WS handshake (connected message)
  - ping/pong
  - list_tools
  - call_tool  (text + image)
  - execute_luau
  - studio_status
  - restart_mcp
  - Error handling for unknown tools

Usage:
    py tests/e2e/test_full_cycle.py
"""

import sys, os, json, asyncio, subprocess, time, signal, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
BRIDGE_PY = os.path.join(ROOT, "bridge", "bridge.py")
MOCK_PY = os.path.join(HERE, "mock_mcp.py")
CONFIG_JSON = os.path.join(ROOT, "bridge", "config.json")
TEST_PORT = 18613
passed = 0
failed = 0

def log(msg, ok=True):
    global passed, failed
    if ok: passed += 1; print(f"  PASS: {msg}")
    else: failed += 1; print(f"  FAIL: {msg}")

async def connect_ws(port, timeout=10):
    import websockets
    return await asyncio.wait_for(
        websockets.connect(f"ws://127.0.0.1:{port}"), timeout=timeout
    )

async def send_and_wait(ws, msg, timeout=15):
    await ws.send(json.dumps(msg))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=1)
            resp = json.loads(raw)
            if resp.get("id") == msg.get("id"): return resp
        except asyncio.TimeoutError: continue
        except: return None
    return None

def setup_config():
    backup = CONFIG_JSON + ".bak"
    if os.path.exists(CONFIG_JSON) and not os.path.exists(backup):
        shutil.copy2(CONFIG_JSON, backup)
    mock_cfg = {
        "mcpServers": {
            "mock": {
                "command": sys.executable,
                "args": [MOCK_PY]
            }
        }
    }
    with open(CONFIG_JSON, "w", encoding="utf-8") as f:
        json.dump(mock_cfg, f, indent=2)

def restore_config():
    backup = CONFIG_JSON + ".bak"
    if os.path.exists(backup):
        shutil.move(backup, CONFIG_JSON)
    elif os.path.exists(CONFIG_JSON):
        os.remove(CONFIG_JSON)

async def run_tests():
    print("\n=== E2E: Bridge Full Cycle (mock mode) ===\n")

    bridge_proc = None

    try:
        # 1. Write mock config
        setup_config()

        # 2. Start bridge
        print("  Starting bridge + mock MCP...")
        bridge_proc = subprocess.Popen(
            [sys.executable, BRIDGE_PY],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env={**os.environ, "ZS_BRIDGE_PORT": str(TEST_PORT)}
        )
        await asyncio.sleep(5)
        if bridge_proc.poll() is not None:
            log("bridge failed to start", False)
            return False
        log("bridge + mock MCP server started")

        # 3. Connect WebSocket
        ws = await connect_ws(TEST_PORT)
        log("WebSocket connected")

        # 5. Connected message
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        connected = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        if isinstance(connected, dict) and connected.get("type") == "connected":
            log("connected message received (type=connected)")
        else:
            log(f"expected connected, got {connected.get('type', '?')}", False)

        # 6. Ping/Pong
        pong = await send_and_wait(ws, {"type": "ping", "id": 1})
        if pong and pong.get("type") == "pong":
            log("ping/pong")
        else:
            log(f"pong fail: {pong}", False)

        # 7. List tools
        tools_resp = await send_and_wait(ws, {"type": "list_tools", "id": 2})
        if tools_resp and tools_resp.get("type") == "tools":
            tools = tools_resp.get("tools", [])
            tool_names = [t["name"] for t in tools]
            log(f"list_tools returned {len(tools)} tools")
            assert "execute_luau" in tool_names, "execute_luau in tools"
            assert "screen_capture" in tool_names, "screen_capture in tools"
            assert "multi_edit" in tool_names, "multi_edit in tools"
            log("critical tools present (execute_luau, screen_capture, multi_edit)")
        else:
            log(f"list_tools fail: {tools_resp}", False)

        # 8. Studio status
        status_resp = await send_and_wait(ws, {"type": "studio_status", "id": 3})
        if status_resp and status_resp.get("type") == "studio_status":
            log(f"studio_status: ok")
        else:
            log(f"studio_status fail: {status_resp}", False)

        # 9. Restart MCP
        restart_resp = await send_and_wait(ws, {"type": "restart_mcp", "id": 4, "server": None})
        if restart_resp and restart_resp.get("type") == "mcp_status":
            log(f"restart_mcp: ok={restart_resp.get('ok')}")
        else:
            log(f"restart_mcp fail: {restart_resp}", False)

        # 10. Call tool: screen_capture
        sc_resp = await send_and_wait(ws, {
            "type": "call_tool", "id": 5,
            "name": "screen_capture", "arguments": {}, "timeout": 60000
        }, timeout=30)
        if sc_resp and sc_resp.get("type") == "tool_result":
            ok = sc_resp.get("ok", False)
            has_images = len(sc_resp.get("images", [])) > 0
            has_text = bool(sc_resp.get("text", ""))
            log(f"screen_capture: ok={ok}, text={has_text}, images={has_images}")
        else:
            log(f"screen_capture fail: {sc_resp}", False)

        # 11. Call tool: execute_luau
        exec_resp = await send_and_wait(ws, {
            "type": "call_tool", "id": 6,
            "name": "execute_luau",
            "arguments": {"code": "print('hello')"},
            "timeout": 60000
        }, timeout=30)
        if exec_resp and exec_resp.get("type") == "tool_result":
            log(f"execute_luau: ok={exec_resp.get('ok')}, text={bool(exec_resp.get('text',''))}")
        else:
            log(f"execute_luau fail: {exec_resp}", False)

        # 12. Error: unknown tool
        err_resp = await send_and_wait(ws, {
            "type": "call_tool", "id": 7,
            "name": "nonexistent_tool_xyz", "arguments": {}, "timeout": 30000
        }, timeout=15)
        if err_resp and err_resp.get("type") == "tool_result":
            ok = err_resp.get("ok", True) is False
            has_error = bool(err_resp.get("error", ""))
            log(f"unknown tool error: ok=false={ok}, has_error={has_error}")
        else:
            log(f"unknown tool error response: {err_resp}", False)

        # 13. Call tool: script_read
        read_resp = await send_and_wait(ws, {
            "type": "call_tool", "id": 8,
            "name": "script_read",
            "arguments": {"path": "game.ServerScriptService.TestScript"},
            "timeout": 60000
        }, timeout=30)
        if read_resp and read_resp.get("type") == "tool_result":
            log(f"script_read: ok={read_resp.get('ok')}")
        else:
            log(f"script_read fail: {read_resp}", False)

        # 14. Call tool: script_create
        create_resp = await send_and_wait(ws, {
            "type": "call_tool", "id": 9,
            "name": "script_create",
            "arguments": {"path": "game.ServerScriptService.NewScript", "contents": "-- test"},
            "timeout": 60000
        }, timeout=30)
        if create_resp and create_resp.get("type") == "tool_result":
            log(f"script_create: ok={create_resp.get('ok')}")
        else:
            log(f"script_create fail: {create_resp}", False)

        await ws.close()
        log("WebSocket closed cleanly")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        for i in range(passed + failed + 1, 15):
            log(f"test {i} (not reached)", False)
    finally:
        # Cleanup — bridge will kill its child processes
        if bridge_proc and bridge_proc.poll() is None:
            bridge_proc.terminate()
            try: bridge_proc.wait(timeout=5)
            except: bridge_proc.kill()
        restore_config()

    print(f"\n=== Results: {passed} passed, {failed} failed, {passed + failed} total ===")
    return failed == 0

if __name__ == "__main__":
    result = asyncio.run(run_tests())
    sys.exit(0 if result else 1)
