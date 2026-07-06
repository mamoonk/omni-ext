# Omni-Ext — Build Plan

**Goal:** Reimplement ZeroScript-Free: a browser extension + local bridge that turns free AI chats (DeepSeek, Gemini, etc.) into a Roblox Studio agent via MCP.

---

## Architecture

```
AI Chat (DeepSeek/Gemini/etc.)   ←→   Browser Extension   ←→   Bridge (Python)   ←→   Roblox Studio MCP
                                         (content script)        (WS :17613)           (stdio)
```

---

## Phase 1 — Bridge (Python)

Standalone WebSocket server that translates extension commands into MCP calls.

### Files

| File | Purpose |
|------|---------|
| `bridge/bridge.py` | WebSocket server on `ws://127.0.0.1:17613`. Routes `call_tool`, `list_tools`, `studio_status`. Manages MCPClient pool. |
| `bridge/launch_studio_mcp.py` | Finds newest `StudioMCP.exe` across Roblox version folders (avoids broken `mcp.bat`). |
| `bridge/config.json` | Declares MCP servers to spawn (default: `roblox` → `launch_studio_mcp.py`). |
| `bridge/start.bat` | Detects Python, installs `websockets` via pip, launches `bridge.py`. |

### Key Classes

- **MCPClient** — spawns an MCP server as a stdio child. Threaded reader matches JSON-RPC responses by `id`. Auto-restarts on death. Retries once on transient Studio drops.
- **MCPManager** — aggregates multiple MCP servers, builds a tool name index (handles collisions with `server/` prefix).
- **probe_studio()** — two-level health check: `list_roblox_studios` (is Studio connected?) + `get_studio_state` (is a place loaded?).

### Protocol (Extension ↔ Bridge)

All JSON over WebSocket:

```
→ {"type":"list_tools"}
← {"type":"tools","tools":[...],"mcp_alive":true,"studio":true}

→ {"type":"call_tool","name":"execute_luau","arguments":{"code":"..."},"timeout":120000}
← {"type":"tool_result","id":1,"ok":true,"text":"...","images":[]}

→ {"type":"studio_status"}
← {"type":"studio_status","studio":true,"studio_app":true,"mcp_alive":true}

→ {"type":"ping"}
← {"type":"pong"}
```

### Status Dot

| State | Meaning |
|-------|---------|
| Green | Bridge + Studio ready (place open) |
| Yellow | Bridge OK, Studio not usable yet |
| Grey | Bridge offline |

---

## Phase 2 — Extension Foundation (Chrome MV3)

### Files

| File | Purpose |
|------|---------|
| `extension/manifest.json` | Permissions, host patterns, content script matches |
| `extension/background.js` | Service worker: WebSocket to bridge, pending request map, heartbeat, reconnect |
| `extension/core/config.js` | System prompt, tool definitions, feedback strings |
| `extension/core/parser.js` | Parse AI output for `command(args)` patterns |
| `extension/core/main.js` | Agentic loop, UI overlay, session state (provider-agnostic) |
| `extension/overlay.css` | Panel/bar styling |
| `extension/popup.html` | Extension popup |
| `extension/popup.js` | Popup logic |

### How the Agentic Loop Works (core/main.js)

1. User types a request in the AI chat
2. Extension injects system prompt describing available tools
3. AI replies with tool commands like `execute_luau(code="print(1)")`
4. `parser.js` extracts the command
5. `main.js` sends it via `background.js` WS → Bridge → Studio MCP
6. Studio executes and returns result
7. Extension injects result back into the chat
8. AI sees the result and continues autonomously

### Provider Interface (ZSProvider)

Each provider file exports the same interface:

- `isComposerReady()` — is the input field available?
- `getReplyText()` — read the last AI response
- `sendMessage(text)` — inject text into the chat
- `onGenerationStart(cb)` / `onGenerationEnd(cb)` — detect when AI starts/stops replying
- `getSendButton()` / `getInputArea()` — DOM selectors
- `maskCodeBlocks(text)` — camouflage injected results

---

## Phase 3 — Provider Integrations

One JS file per AI chat site. Each adapts the ZSProvider interface to that site's DOM.

| Provider | File | DOM Framework | Complexity |
|----------|------|---------------|------------|
| DeepSeek | `extension/providers/deepseek.js` | React | Easy |
| Gemini | `extension/providers/gemini.js` | Angular + Quill | Medium |
| Kimi | `extension/providers/kimi.js` | Vue + Lexical | Medium |
| GLM | `extension/providers/glm.js` | Svelte | Medium |
| Qwen | `extension/providers/qwen.js` | Vue + Monaco | Hard (needs SSE tap) |
| Qwen (net) | `extension/providers/qwen-net.js` | MAIN-world fetch tap | — |
| Arena | `extension/providers/arena.js` | React | Medium |

**Strategy:** Build DeepSeek first. Add others after core loop is solid.

---

## Phase 4 — Polish

- Project memory (persistent notes about the place, carried across sessions)
- Custom prompt (user-supplied instructions appended to system prompt)
- Stop button
- Error recovery in agentic loop
- Session state persistence

---

## Roblox Studio MCP Tools (as of July 2026)

| Category | Tools |
|----------|-------|
| Scripts | `script_read`, `multi_edit`, `script_search`, `script_grep` |
| Assets | `generate_mesh`, `generate_material`, `generate_procedural_model`, `insert_from_creator_store` |
| Data model | `explore_subagent`, `search_game_tree`, `inspect_instance` |
| Execution | `execute_luau` |
| Playtesting | `start_stop_play`, `console_output`, `screen_capture`, `playtest_subagent` |
| Input sim | `character_navigation`, `keyboard_input`, `mouse_input` |
| Sessions | `list_roblox_studios`, `set_active_studio` |

Source: https://create.roblox.com/docs/studio/mcp — the built-in MCP server auto-updates with Studio.

---

## Sources for Latest Information

| Source | URL |
|--------|-----|
| Roblox MCP docs | https://create.roblox.com/docs/studio/mcp |
| Roblox DevForum announcements | https://devforum.roblox.com/t/assistant-updates-studio-built-in-mcp-server-and-playtest-automation/4474643 |
| Official OSS MCP server | https://github.com/Roblox/studio-rust-mcp-server |
| Community MCP server (Chrrxs) | https://github.com/Chrrxs/robloxstudio-mcp |
| MCP Roblox docs server | https://github.com/n4tivex/mcp-roblox-docs |
| Creator Hub docs | https://create.roblox.com/docs |

---

## Estimated Timeline

| Phase | Time |
|-------|------|
| Phase 1 — Bridge | 2–4 days |
| Phase 2 — Extension core | 3–5 days |
| Phase 3 — DeepSeek provider | 2–3 days |
| Phase 3 — Additional providers | 1–3 days each |
| Phase 4 — Polish | 2–4 days |
| **Total (DeepSeek only)** | **~2 weeks** |
| **Total (all providers)** | **~4–8 weeks** |

---

## Project Structure (Final)

```
omni-ext/
├── PLAN.md
├── bridge/
│   ├── bridge.py
│   ├── launch_studio_mcp.py
│   ├── config.json
│   ├── start.bat
│   └── logs/
├── extension/
│   ├── manifest.json
│   ├── background.js
│   ├── popup.html
│   ├── popup.js
│   ├── overlay.css
│   ├── icon.png
│   ├── core/
│   │   ├── config.js
│   │   ├── parser.js
│   │   └── main.js
│   └── providers/
│       ├── deepseek.js
│       ├── gemini.js
│       ├── kimi.js
│       ├── glm.js
│       ├── qwen.js
│       ├── qwen-net.js
│       └── arena.js
└── assets/
```
