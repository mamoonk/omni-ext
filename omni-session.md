# Omni-Ext Session Log

## 2026-07-05 — Initial Build

### Phase 1 — Bridge (Python) ✅
- `bridge/bridge.py` — WebSocket server on `ws://127.0.0.1:17613`, MCP client with JSON-RPC response matching, auto-restart, Studio connectivity probe, 22 Roblox tools proxied, infinite loop guard
- `bridge/launch_studio_mcp.py` — Finds newest StudioMCP.exe across Roblox version folders, avoids broken mcp.bat
- `bridge/config.json` — Declares roblox MCP server
- `bridge/start.bat` — Python detection (py launcher → PATH → winget install), pip install websockets, port conflict detection, launches bridge

### Phase 2 — Extension Foundation ✅
- `extension/manifest.json` — MV3, unified MAIN-world net-intercept + per-provider isolated-world scripts
- `extension/background.js` — WebSocket to bridge, heartbeat, stale socket detection, reconnect with exponential backoff, request/response routing
- `extension/core/config.js` — 19 tool definitions + strict modern Roblox coding rules (12 rules)
- `extension/core/parser.js` — Regex-based `TOOL_CALL: name(args)` parser
- `extension/core/net-intercept.js` — Universal network interceptor (MAIN world, `document_start`)
- `extension/core/main.js` — Agentic loop, diff preview modal, approval gate
- `extension/overlay.css` — Bar + diff modal styling

### Phase 3 — Providers (Network Interception Architecture) ✅
All providers are thin send-only shims (5–10 lines). No DOM scraping for reading.

- `extension/providers/deepseek.js` — DOM send only
- `extension/providers/gemini.js` — DOM send only
- `extension/providers/kimi.js` — DOM send only
- `extension/providers/glm.js` — DOM send only
- `extension/providers/qwen.js` — DOM send only
- `extension/providers/qwen-net.js` — Deprecated (absorbed into net-intercept)
- `extension/providers/arena.js` — DOM send only

### Phase 4 — Assets ✅
- `extension/icon.png`, `popup.html`, `popup.js`

---

## Architecture: Network Interception Over DOM Scraping

`core/net-intercept.js` (MAIN world, `document_start`) hooks `window.fetch` + `XMLHttpRequest` across all 6 providers. Accumulates streaming responses into `#__zs_net_data` DOM element (`dataset.text` / `dataset.seq` / `dataset.active`). Synced to isolated world every 200ms.

Provider files reduced from ~55 lines to 5–10 lines (send only).

---

## Architecture: Diff Preview & Human Approval Gate

**Problem:** AI uses `multi_edit` to modify multiple scripts. Studio's Undo stack doesn't group MCP changes → Ctrl+Z only undoes the last edit, leaving game broken.

**Solution:** Before `multi_edit` is sent to the bridge, the extension intercepts it:

1. Agent loop detects `multi_edit` call → shows modal (all other commands pass through automatically)
2. Modal reads current script content via `script_read(path)` 
3. Computes line-by-line diff (applies edits in memory, shows +/- lines with color coding)
4. Displays path, edit count, and diff in a dark-themed overlay
5. User clicks [Approve] or [Reject]
6. If approved, `multi_edit(path, edits)` is sent to bridge
7. If rejected, the call is skipped and agent loop continues

**Safe commands** (no modal required): script_read, script_search, script_grep, execute_luau, inspect_instance, search_game_tree, list_roblox_studios, set_active_studio, generate_mesh, generate_material, generate_procedural_model, insert_from_creator_store, start_stop_play, console_output, screen_capture, character_navigation, keyboard_input, mouse_input, explore_subagent — 19 safe tools.

**Only `multi_edit` requires approval** — it's the only tool that can silently break scripts without Studio-level undo grouping.

---

## Critical Risk: execute_luau Infinite Loop Protection ⚠️

**Mitigation in `bridge.py` (`_wl` function):** Every `execute_luau` call wrapped in `pcall()`, 15s `os.clock()` deadline injected into while/numeric-for/repeat loops. Bridge MCP timeout (30s) as second layer.
