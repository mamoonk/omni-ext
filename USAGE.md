# Omni-Ext — Detailed Usage Guide

## Table of Contents

1. [Installation](#1-installation)
2. [Bridge Setup](#2-bridge-setup)
3. [Extension Setup](#3-extension-setup)
4. [Roblox Studio Setup](#4-roblox-studio-setup)
5. [First Session](#5-first-session)
6. [Agent Loop Deep-Dive](#6-agent-loop-deep-dive)
7. [Tool Reference](#7-tool-reference)
8. [Multi_Edit Approval Flow](#8-multi_edit-approval-flow)
9. [Custom Instructions & Memory](#9-custom-instructions--memory)
10. [Working with Multiple Studios](#10-working-with-multiple-studios)
11. [Debugging](#11-debugging)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Installation

### What You Need

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Download from [python.org](https://python.org) |
| Chrome / Edge | Latest | MV3 extension support required |
| Roblox Studio | Latest | Enable MCP server in settings |
| `websockets` | — | Python package (installed automatically) |

### Step 1: Get the Code

```bash
git clone https://github.com/mamoonk/omni-ext.git
cd omni-ext
```

### Step 2: Install Bridge Dependencies

```bash
pip install websockets
```

To verify:

```bash
python -c "import websockets; print(websockets.__version__)"
# Should print: 15.0.1 (or similar)
```

### Step 3: Verify Everything Works

```bash
# Run all tests
pytest tests/unit/bridge/ -v
node tests/unit/extension/test_config.js
node tests/integration/test_agent_loop.js

# Run the full E2E test (auto-starts mock MCP + bridge)
python tests/e2e/test_full_cycle.py
```

All tests should pass with 0 failures.

---

## 2. Bridge Setup

### Launch the Bridge

**Option A — Command line:**

```bash
cd bridge
python bridge.py
```

**Option B — Double-click** (Windows only):

Double-click `bridge/start.bat`.

### What You Should See

```
  Omni-Ext Bridge - ws://127.0.0.1:17613

21:27:46 ===== START pid=5640 =====
21:27:46 configured 1 server(s): roblox
21:27:46 [roblox] launch (python launch_studio_mcp.py)
21:27:47 [roblox] up (21 tools)
21:27:47 listening on ws://127.0.0.1:17613
```

If Roblox Studio is not running or MCP is not enabled, you'll see:

```
21:27:47 ---
21:27:47 0 tools loaded - Studio not exposing tools yet
21:27:47 Open Studio + enable MCP server
21:27:47 ---
21:27:47 listening on ws://127.0.0.1:17613
```

The bridge will automatically connect once Studio is ready.

### Port Configuration

The bridge listens on port `17613` by default. Override with the `ZS_BRIDGE_PORT` environment variable:

```bash
# Windows (PowerShell)
$env:ZS_BRIDGE_PORT='17614'; python bridge.py

# Windows (CMD)
set ZS_BRIDGE_PORT=17614 && python bridge.py
```

---

## 3. Extension Setup

### Load the Extension in Chrome

1. Open **`chrome://extensions`**
2. Toggle **Developer mode** ON (top-right corner)
3. Click **Load unpacked**
4. Select the **`extension/`** folder inside `omni-ext/`
5. Pin the Omni-Ext icon to the toolbar ![icon](extension/icon.png)

### Verify the Extension Loaded

You should see:

```
Omni-Ext Roblox Studio Agent
Version 0.2.0
ID: [extension ID]
Inspect views: service worker
```

The extension injects content scripts into these sites:
- `chat.deepseek.com`
- `gemini.google.com`
- `www.kimi.com`
- `chat.z.ai`
- `arena.ai`
- `chat.qwen.ai`

### Permissions

The extension requests:
- `storage` — saves custom instructions and project memory
- Host access to the 6 chat platforms (to inject scripts)
- Host access to `127.0.0.1` — WebSocket connection to the bridge

---

## 4. Roblox Studio Setup

### Enable MCP Server

1. Open **Roblox Studio**
2. Open any place or create a new one
3. Go to **File → Studio Settings**
4. Navigate to **MCP Server**
5. Toggle **Enable MCP Server** ON
6. The bridge log should change to:

```
21:27:47 Studio connected (21 tools)
21:27:47 ready (21 tools)
```

### MCP Server Port

Studio's MCP server runs on port **13469** by default (hardcoded in `bridge.py:13`). The bridge connects automatically — no configuration needed.

### Verify Connectivity

When both bridge and Studio are ready, the extension bar changes from **● Bridge offline** to **● Ready**.

---

## 5. First Session

### Step-by-Step

1. **Start the bridge** (see §2)

2. **Open a chat platform** — go to one of the supported sites:
   - [DeepSeek Chat](https://chat.deepseek.com)
   - [Gemini](https://gemini.google.com)
   - [Kimi](https://www.kimi.com)
   - [Z.AI (GLM)](https://chat.z.ai)
   - [Arena](https://arena.ai)
   - [Qwen](https://chat.qwen.ai)

3. **Check the bar** — A dark bar appears at the top of the page:
   ```
   ┌──────────────────────────────────────────────────────┐
   │ Omni-Ext ● Ready [📝][⚙][▶ Start]                    │
   └──────────────────────────────────────────────────────┘
   ```
   - **●** — Green = ready, Yellow = no Studio, Red = bridge offline
   - **📝** — Project memory (persistent across sessions)
   - **⚙** — Custom instructions
   - **▶ Start** — Begin the agent loop

4. **Click ▶ Start** — The agent loop begins polling for AI output

5. **Chat with the AI** — Ask it to do something in your Roblox game:

   ```
   Can you add a part to the workspace and give it a script?
   ```

6. **Watch the tools fire** — The bar shows status updates:
   ```
   Omni-Ext ● Running script_create...
   Omni-Ext ● Agent running
   ```

7. **Results appear in chat** — The AI shows the tool output and responds.

### Example Session

```
You: Add a part named "MyPart" to the workspace and insert a script that prints "hello"

AI: [thinking]
    TOOL_CALL: execute_luau(code="local p=Instance.new('Part') p.Name='MyPart' p.Parent=workspace")
    [Result]
    [mock execute_luau ok]
    
    TOOL_CALL: script_create(path="game.Workspace.MyPart.Script", contents="print('hello')")
    [Result]
    [mock script_create ok]
    
    Done! Added MyPart to the workspace with a script.
```

> **Note:** This is a mock output. Real results show actual Studio responses.

---

## 6. Agent Loop Deep-Dive

### Loop Mechanics

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Poll every   │────▶│ Parse for    │────▶│ Check SAFE   │
│ 300ms        │     │ TOOL_CALL:   │     │ list         │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                     ┌───────────┴───────────┐
                                     │                       │
                                  SAFE                   NOT SAFE
                                     │                       │
                                     ▼                       ▼
                             ┌──────────────┐     ┌──────────────────┐
                             │ Enqueue call  │     │ Show approval    │
                             │ (FIFO queue)  │     │ modal (multi_edit│
                             └──────┬───────┘     │ only)            │
                                    │             └────────┬─────────┘
                                    ▼                      │
                             ┌──────────────┐              │
                             │ Send via     │◀─────────────┘
                             │ background   │    if approved
                             │ → bridge     │
                             │ → Studio MCP │
                             └──────┬───────┘
                                    │
                                    ▼
                             ┌──────────────┐     ┌──────────────┐
                             │ Format result │────▶│ Inject back  │
                             │ (text/images) │     │ into chat    │
                             └──────────────┘     └──────────────┘
```

### Key Details

**Polling** (`main.js:poll()`)
- Runs every 300ms via `setInterval`
- Checks `__zs_net_data` element for new text (`dataset.seq` increments)
- `_isProcessing` flag and FIFO queue prevent concurrent calls

**Parsing** (`parser.js:_parseToolCall()`)
- Scans for `TOOL_CALL:` followed by `name(` 
- Uses char-by-char balanced-paren scanner (handles `)` inside quoted strings)
- Extracts args: `key="val"`, `key='val'`, `key=123`, `key=true`
- Returns `{name, args}` or `null` if no valid call

**Queue** (`main.js:_queue`)
- New calls while one is in-flight are queued
- Processed sequentially in FIFO order
- Each result is sent back to the AI before the next call fires

### SAFE List

19 tools execute automatically. Only `multi_edit` requires manual approval.

| Category | Safe Tools |
|---|---|
| Script | `script_read`, `script_create`, `script_search`, `script_grep` |
| Execution | `execute_luau`, `inspect_instance`, `search_game_tree` |
| Studio | `list_roblox_studios`, `set_active_studio` |
| 3D | `generate_mesh`, `generate_material`, `generate_procedural_model`, `insert_from_creator_store` |
| Playtest | `start_stop_play`, `console_output`, `screen_capture` |
| Input | `character_navigation`, `keyboard_input`, `mouse_input` |
| **Requires approval** | `multi_edit` |

### Image Injection

When a tool returns images (e.g., `screen_capture`), the extension injects them into the chat input automatically:
- **Contenteditable inputs** (Gemini, Kimi, GLM, Arena, Qwen): inline `<img>` tag
- **Textarea inputs** (DeepSeek): markdown `![screenshot](data:image/png;base64,...)` data URI

The send button is clicked automatically after injection.

---

## 7. Tool Reference

### script_read `path`

Read the full contents of a script by its dot-path.

```luau
TOOL_CALL: script_read(path="game.ServerScriptService.MyScript")
```

Returns the script source as text.

### script_create `path`, `contents`

Create a new script at the given path with the given contents.

```luau
TOOL_CALL: script_create(path="game.Workspace.MyPart.Script", contents="print('hello')")
```

Fails if the target already exists. Use `multi_edit` to update existing scripts.

### script_search `query`

Search scripts by name. Returns matching paths.

```luau
TOOL_CALL: script_search(query="MyScript")
```

### script_grep `pattern`

Grep script contents across all scripts.

```luau
TOOL_CALL: script_grep(pattern="while")
```

### execute_luau `code`

Execute arbitrary Luau code in Studio. Automatically wrapped in safety guards:

- A 15-second execution deadline is injected into all loops
- Dangerous APIs (`writefile`, `http_request`, `loadstring`, etc.) are blocked
- The code is wrapped in `pcall()` to catch errors

```luau
TOOL_CALL: execute_luau(code="print(workspace.Name)")
```

Good for: inspecting state, creating/modifying instances, testing logic.

### inspect_instance `path`

Get detailed properties of a Roblox instance.

```luau
TOOL_CALL: inspect_instance(path="game.Workspace.MyPart")
```

Returns all properties (Name, ClassName, Position, Size, Color, etc.).

### search_game_tree `path`

Browse the game explorer tree from a given path.

```luau
TOOL_CALL: search_game_tree(path="game.Workspace")
```

Returns child names and counts.

### screen_capture

Capture the current Studio viewport as a PNG image.

```luau
TOOL_CALL: screen_capture()
```

Returns both text description and image data.

### generate_mesh `prompt`

Generate a 3D mesh from a text prompt.

```luau
TOOL_CALL: generate_mesh(prompt="a red apple")
```

### generate_material `prompt`

Generate a material from a text prompt.

```luau
TOOL_CALL: generate_material(prompt="brick texture")
```

### generate_procedural_model `prompt`

Generate a procedural model from a text prompt.

```luau
TOOL_CALL: generate_procedural_model(prompt="a futuristic sword")
```

### insert_from_creator_store `assetId`

Insert an asset from the Creator Store.

```luau
TOOL_CALL: insert_from_creator_store(assetId=12345678)
```

### start_stop_play `action`

Start or stop playtesting.

```luau
TOOL_CALL: start_stop_play(action="start")
TOOL_CALL: start_stop_play(action="stop")
```

### console_output

Get the playtest console output.

```luau
TOOL_CALL: console_output()
```

### list_roblox_studios

List connected Roblox Studio instances.

```luau
TOOL_CALL: list_roblox_studios()
```

Useful when multiple Studio windows are open.

### set_active_studio `id`

Set the active Studio instance by ID.

```luau
TOOL_CALL: set_active_studio(id="studio-id-here")
```

### character_navigation

Move the character to a position or instance.

```luau
TOOL_CALL: character_navigation(x=10, y=5, z=0)
TOOL_CALL: character_navigation(instancePath="game.Workspace.MyPart")
```

### keyboard_input `keys`, `holdMs`

Simulate keyboard input.

```luau
TOOL_CALL: keyboard_input(keys="W", holdMs=500)
```

### mouse_input `action`, `x`, `y`

Simulate mouse actions.

```luau
TOOL_CALL: mouse_input(action="click", x=500, y=300)
TOOL_CALL: mouse_input(action="move", x=600, y=400)
TOOL_CALL: mouse_input(action="scroll", x=0, y=-100)
```

### multi_edit `path`, `edits`

Edit a script with line-level changes. This is the only tool that requires manual approval.

```luau
TOOL_CALL: multi_edit(path="game.ServerScriptService.MyScript", edits=[{line=1, text="print('hello')"}, {line=2, text="print('world')"}])
```

When the AI uses `multi_edit`, a modal appears showing:
- The file path
- Number of edits
- Line-by-line diff (green = added, red = removed, gray = unchanged)
- [Approve] / [Reject] buttons

---

## 8. Multi_Edit Approval Flow

`multi_edit` requires explicit approval because Studio's Undo stack (Ctrl+Z) undoes individual edits, not the entire multi-edit batch. This means a failed batch can leave scripts in a broken state.

### What Happens

1. **AI sends** `TOOL_CALL: multi_edit(path="X", edits=[...])`
2. **Extension detects** it's not in the SAFE list
3. **Reads current content** via `script_read(path)` to compute a diff
4. **Shows modal:**

```
┌──────────────────────────────────────────────────────────┐
│ AI wants to modify 3 edit(s) in workspace.MyScript      │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 1                                                        │
│ │ - print("old")                                          │
│ │ + print("new")                                          │
│ │ 2                                                        │
│ │ - x = 1                                                  │
│ │ + x = 2                                                  │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│              [Reject]          [Approve]                  │
└──────────────────────────────────────────────────────────┘
```

5. **Approve** — sends `multi_edit` to the bridge
6. **Reject** — skips the call; agent loop continues

### Tips

- If the diff preview looks wrong, **Reject**
- You can modify the custom instructions to ask the AI to use `execute_luau` instead when possible (it bypasses the modal)
- The preview only shows the first 10 edits inline; more than 10 shows a summary list

---

## 9. Custom Instructions & Memory

Two buttons on the bar provide persistent context:

### Custom Instructions (⚙)

Clicking the **⚙** button opens a prompt dialog. Whatever you type is prepended to the system prompt on every session start.

Use cases:
- **Role setting:** "You are a senior Roblox scripter"
- **Style guide:** "Always use _ for private variables"
- **Constraints:** "Never delete scripts, only modify"
- **Workflow:** "Always test with execute_luau before writing scripts"

```javascript
// Saved to chrome.storage.local as 'zsp'
{ zsp: "You are a senior Roblox scripter. Always use _ for private variables.", zsm: "" }
```

### Project Memory (📝)

Clicking the **📝** button opens a prompt dialog. The value is injected as:

```
Project memory:
<your text>
```

Use cases:
- **Game overview:** "This is an obby game with 10 levels"
- **Place structure:** "All modules are in ReplicatedStorage.Modules"
- **Progress tracking:** "We're working on the save system"
- **Known issues:** "The leaderboard has a race condition"

```javascript
// Saved to chrome.storage.local as 'zsm'
{ zsp: "", zsm: "This is an obby game with 10 levels. All modules are in ReplicatedStorage.Modules." }
```

### Persistence

Both values survive:
- Page refreshes
- Browser restarts
- Extension reloads

They do NOT sync across devices (local storage only).

---

## 10. Working with Multiple Studios

### Listing Studios

```
TOOL_CALL: list_roblox_studios()
```

Returns a list of connected Studio instances with IDs.

### Switching Active Studio

```
TOOL_CALL: set_active_studio(id="studio-id")
```

All subsequent tool calls go to the selected Studio.

### Bridge Config

The bridge can manage multiple MCP servers. The config file (`bridge/config.json`) defines them:

```json
{
  "mcpServers": {
    "roblox": {
      "command": "launch_studio_mcp.py",
      "args": []
    }
  }
}
```

To add another server, add a new entry with a unique key, command, and args.

---

## 11. Debugging

### Bridge Logs

The bridge prints color-coded logs to the terminal:

| Color | Meaning |
|---|---|
| `96` (cyan) | Startup, restart, tool call |
| `92` (green) | Success (connected, ready) |
| `93` (yellow) | Warning (retry, no tools) |
| `91` (red) | Error (crash, timeout) |

### Bridge Debug Log File

All logs are also written to `bridge/logs/bridge_debug.log`. Check this file if the terminal output is lost.

### Extension Console

Open the extension's service worker console:
1. Go to `chrome://extensions`
2. Click **service worker** (under Omni-Ext)
3. The console shows WebSocket connection status, tool calls, and errors

### Extension Popup

Click the Omni-Ext icon in the toolbar to see the popup with basic status info.

### Tool Status Bar

The omnibar at the top of the chat page shows:

| Indicator | Meaning |
|---|---|
| ● gray | Bridge offline |
| ● yellow | Bridge connected, but Studio not ready |
| ● green | Bridge + Studio ready |
| ● orange | Waiting for approval |
| ● purple | Running tool |
| ● red | Error / stopped |

### Verifying Network Interception

To check if the network interceptor is working:

1. Open DevTools on the chat page (F12)
2. Go to **Console**
3. Check for any `[ZS]` prefixed messages
4. In the **Elements** tab, search for `__zs_net_data`
5. The element's `dataset` attributes show the current intercepted text

---

## 12. Troubleshooting

### "Bridge offline" on the bar

| Cause | Fix |
|---|---|
| Bridge not running | Start the bridge (`python bridge/bridge.py`) |
| Wrong port | Default is 17613. Check `ZS_BRIDGE_PORT` env var |
| Firewall blocking | Allow Python through Windows Firewall |
| Extension not injected | Reload the chat page |

### "Studio not ready"

| Cause | Fix |
|---|---|
| Studio not running | Open Roblox Studio |
| MCP server disabled | Enable in Studio Settings |
| Studio just started | Wait ~10 seconds for MCP to initialize |
| Place not open | Open or create a place |
| Bridge not connected | Restart the bridge |

### Tools not executing

| Cause | Fix |
|---|---|
| Tool not in SAFE list | Only `multi_edit` requires approval |
| Agent loop not started | Click **▶ Start** |
| AI didn't call a tool | Check the AI response for `TOOL_CALL:` |
| Parser failed | Check the AI output for matching `TOOL_CALL: name(args)` format |

### "TypeError: Failed to fetch" (extension popup)

The background service worker can't connect to the bridge. Start the bridge and wait a few seconds.

### Bridge crashes on startup

1. Check Python version: `python --version` (need 3.10+)
2. Install websockets: `pip install websockets`
3. Check port conflict: `netstat -ano | findstr :17613`
4. Check bridge debug log: `bridge/logs/bridge_debug.log`

### Multi_edit modal not showing

- `multi_edit` is the only tool that triggers the modal
- If the AI uses `execute_luau` with inline edits, it bypasses the modal
- Check that the AI's response contains `TOOL_CALL: multi_edit(...)`

### DeepSeek image pasting not working

DeepSeek uses a `<textarea>` input, which doesn't support `ClipboardEvent` with files. The extension falls back to embedding a markdown image data URI (`![screenshot](data:...)`). This works with all textarea-based inputs.

### Agent loop stopped

The agent loop automatically stops when:
- **■ Stop** is clicked
- The bridge disconnects
- An error occurs

Click **▶ Start** to resume.

### Can I use multiple chat platforms at once?

Yes. The extension injects into each platform independently. You can have DeepSeek, Gemini, and Kimi open simultaneously, each with its own agent loop. All route through the same bridge to the same Studio instance.

### The AI keeps retrying the same tool

If a tool call fails, the AI sees the error and may retry. Common causes:
- `execute_luau` code has a syntax error
- `script_read` path doesn't exist
- `screen_capture` fails because Studio is minimized
- `multi_edit` was rejected by the user

Add "If a tool fails, explain the error and try a different approach" to custom instructions.
