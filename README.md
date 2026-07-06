# Omni-Ext

Turn free AI chat platforms into a Roblox Studio development agent — via network interception + a local bridge.

[![Chrome Extension](https://img.shields.io/badge/platform-Chrome%20Extension-4285F4)](https://img.shields.io/badge/platform-Chrome%20Extension-4285F4) [![Python](https://img.shields.io/badge/bridge-Python%203.12-3776AB)](https://img.shields.io/badge/bridge-Python%203.12-3776AB) [![MCP](https://img.shields.io/badge/protocol-MCP-7c5cfc)](https://img.shields.io/badge/protocol-MCP-7c5cfc) [![License](https://img.shields.io/badge/license-MIT-green)](https://img.shields.io/badge/license-MIT-green)

---

## How It Works

Omni-Ext injects a content script into supported AI chat platforms, intercepts the AI's response stream, and parses `TOOL_CALL:` instructions embedded in the model output. Those instructions are forwarded through a local WebSocket bridge to Roblox Studio's MCP server, which executes them inside Studio.

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Chrome)                        │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              AI Chat Platform (page)                 │ │
│  │  ┌──────────────────────────────────────────┐       │ │
│  │  │  net-intercept.js  ← SSE/response stream │       │ │
│  │  │  provider/*.js     ← send/receive adapter│       │ │
│  │  │  main.js           ← poll + parse + route │       │ │
│  │  └──────────────────────────────────────────┘       │ │
│  └─────────────────────────────────────────────────────┘ │
│                          │ WS (127.0.0.1:17613)           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              background.js (service worker)          │ │
│  │  proxies WS ↔ extension, reloads on disconnect      │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│                 Local Machine                             │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              bridge.py (Python)                      │ │
│  │  ┌──────────────────────────────────────────┐       │ │
│  │  │  WebSocket server (asyncio)              │       │ │
│  │  │  JSON-RPC stdio client → MCP subprocess  │       │ │
│  │  │  Health watchdog + auto-restart          │       │ │
│  │  │  Exponential backoff on crash loop       │       │ │
│  │  └──────────────────────────────────────────┘       │ │
│  └─────────────────────────────────────────────────────┘ │
│                          │ stdio JSON-RPC                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           Roblox Studio MCP Server                   │ │
│  │  execute_luau │ script_read │ screen_capture │ ...  │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Supported Platforms

| Platform | URL | Provider | Status |
|---|---|---|---|
| DeepSeek | `chat.deepseek.com` | `deepseek.js` | ✅ |
| Gemini | `gemini.google.com` | `gemini.js` | ✅ |
| Kimi | `www.kimi.com` | `kimi.js` | ✅ |
| Z.AI (GLM) | `chat.z.ai` | `glm.js` | ✅ |
| Arena | `arena.ai` | `arena.js` | ✅ |
| Qwen | `chat.qwen.ai` | `qwen.js` | ✅ |

---

## Tools

Omni-Ext exposes **21 Roblox Studio tools** through the MCP protocol. The **SAFE list** (19 tools) executes automatically; `multi_edit` requires explicit approval.

### Read / Write

| Tool | Description | Safe |
|---|---|---|
| `script_read` | Read a script by dot-path | ✅ |
| `script_create` | Create a new script | ✅ |
| `script_search` | Search scripts by name | ✅ |
| `script_grep` | Grep script contents | ✅ |
| `multi_edit` | Edit or create with line-level diffs | ⛔ (approval) |

### Execution & Inspection

| Tool | Description | Safe |
|---|---|---|
| `execute_luau` | Run Luau code in Studio | ✅ |
| `inspect_instance` | Get instance properties | ✅ |
| `search_game_tree` | Search the game explorer tree | ✅ |
| `console_output` | Read playtest console logs | ✅ |
| `screen_capture` | Capture viewport screenshot | ✅ |

### 3D / Asset

| Tool | Description | Safe |
|---|---|---|
| `generate_mesh` | Generate a 3D mesh | ✅ |
| `generate_material` | Generate a material | ✅ |
| `generate_procedural_model` | Generate a procedural model | ✅ |
| `insert_from_creator_store` | Insert from Creator Store | ✅ |

### Playtest & Navigation

| Tool | Description | Safe |
|---|---|---|
| `start_stop_play` | Start / stop playtesting | ✅ |
| `character_navigation` | Move character to position | ✅ |
| `keyboard_input` | Simulate keyboard input | ✅ |
| `mouse_input` | Simulate mouse input | ✅ |

### Studio Management

| Tool | Description | Safe |
|---|---|---|
| `list_roblox_studios` | List connected Studio instances | ✅ |
| `set_active_studio` | Set the active Studio instance | ✅ |

### Parse Behaviour

The extension parses `TOOL_CALL: toolName(key="val", key=123)` from the AI's response text. The parser handles:
- Quoted strings (`"..."` and `'...'`)
- Numeric values
- Boolean literals (`true`, `false`)
- Balanced parentheses inside quoted strings

---

## Getting Started

### Prerequisites

- Python 3.10+
- Chrome / Chromium browser
- Roblox Studio (with MCP server enabled)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/omni-ext.git
cd omni-ext

# Install bridge dependencies
pip install websockets

# (Optional) Install test dependencies
pip install pytest pytest-asyncio
```

### Load the Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** and select the `extension/` directory
4. Pin the Omni-Ext icon to the toolbar

### Launch the Bridge

```bash
cd bridge
python bridge.py
```

Or double-click `start.bat` (Windows).

The bridge connects to Roblox Studio's MCP server, loads all available tools, and listens on `ws://127.0.0.1:17613`.

### Connect

1. Open one of the supported AI chat platforms
2. The Omni-Ext bar appears at the top of the page — **● Bridge offline** until the bridge connects
3. Click **▶ Start** to begin the agent loop
4. The AI's responses are intercepted; `TOOL_CALL:` instructions are forwarded to Studio

---

## Architecture

```
extension/
├── manifest.json              # Chrome extension manifest (MV3)
├── background.js              # Service worker — manages WS connection
├── core/
│   ├── config.js              # Tool definitions + system prompt
│   ├── parser.js              # TOOL_CALL: balanced-paren parser
│   ├── main.js                # Agent loop, SAFE list, UI bar, queue
│   └── net-intercept.js       # SSE/response stream interceptor
├── providers/
│   ├── deepseek.js            # DeepSeek chat adapter
│   ├── gemini.js              # Gemini adapter
│   ├── kimi.js                # Kimi adapter
│   ├── glm.js                 # Z.AI / GLM adapter
│   ├── arena.js               # Arena adapter
│   ├── qwen.js                # Qwen adapter
│   └── qwen-net.js            # Qwen network helpers
├── popup.html / popup.js      # Extension popup UI
└── overlay.css                # Bar styling

bridge/
├── bridge.py                  # WS server + MCP client (asyncio)
├── config.json                # MCP server configuration
├── launch_studio_mcp.py       # Studio MCP launcher
└── start.bat                  # Windows launcher

tests/
├── unit/
│   ├── bridge/                # Python unit tests (75)
│   │   ├── test_mcpc.py       # MCP client tests
│   │   ├── test_mcpm.py       # MCP manager tests
│   │   ├── test_sc.py         # Summarization tests
│   │   ├── test_summarize.py  # Tree summarization tests
│   │   └── test_wl.py         # Whitelist tests
│   └── extension/
│       └── test_config.js     # Config / SAFE validation (169)
├── integration/
│   └── test_agent_loop.js     # Agent loop integration (41)
└── e2e/
    ├── test_full_cycle.py     # Full WS protocol E2E (14)
    └── mock_mcp.py            # Mock MCP server for testing
```

---

## Agent Loop

Once started, the agent loop runs every **300ms**:

1. **Poll** the intercepted network response for new text
2. **Parse** any `TOOL_CALL: name(args)` from the text
3. **Safe check** — only SAFE-listed tools execute automatically
4. **Queue** — concurrent calls are serialised via a FIFO queue
5. **Execute** via the bridge → Roblox Studio MCP
6. **Inject** the result (text + optional screenshot) back into the chat

```
┌─────────┐    ┌──────────┐    ┌────────┐    ┌──────────┐    ┌──────────┐
│  Poll   │───▶│  Parse   │───▶│ SAFE?  │───▶│  Queue   │───▶│  Bridge  │
│ 300ms   │    │ TOOL_CALL│    │ check  │    │ FIFO     │    │ → Studio │
└─────────┘    └──────────┘    └────────┘    └──────────┘    └──────────┘
                                                              │
                                                              ▼
┌─────────┐    ┌──────────┐    ┌────────┐
│  Inject │◀───│  Format  │◀───│ Result │
│  to chat│    │ text/img │    │  text  │
└─────────┘    └──────────┘    └────────┘
```

### Image Feedback

If a tool returns images (e.g. `screen_capture`), the extension injects the screenshot directly into the chat input as:
- An inline `<img>` for contenteditable inputs
- A markdown `![screenshot](data:...)` data URI for textarea inputs (DeepSeek)

---

## Bridge Features

### Exponential Backoff

If an MCP server process crashes repeatedly, the bridge applies exponential backoff (1s → 2s → 4s → … → 120s max) before each restart attempt, preventing rapid crash loops.

### Health Watchdog

Every 5 seconds, the bridge checks each configured MCP server. Dead processes are automatically restarted (subject to backoff).

### Studio Presence

A separate watcher polls Roblox Studio's connection state every 4 seconds and logs place open/close events.

### Whitelist (`_wl`)

`execute_luau` code is passed through a whitelist filter that blocks dangerous operations (file I/O, HTTP requests, process spawning) before execution.

---

## Configuration

### Custom Instructions & Memory

Click the **⚙** (custom instructions) or **📝** (project memory) buttons on the extension bar to set persistent prompts. Both values are saved to `chrome.storage.local` and survive page reloads.

### Settings

| Setting | Default | Description |
|---|---|---|
| Custom instructions | `""` | Prepended to the system prompt |
| Project memory | `""` | Injected as "Project memory:\n..." |
| Poll interval | 300ms | How often to check for new AI output |
| Tool timeout | 120s | Max wait for a tool call response |

---

## Scripts

| Command | Description |
|---|---|
| `python bridge/bridge.py` | Start the bridge |
| `start.bat` | Windows launcher for the bridge |
| `python tests/e2e/test_full_cycle.py` | Run E2E protocol tests |

### Running Tests

```bash
# Bridge unit tests (75)
pytest tests/unit/bridge/ -v

# Extension config tests (169)
node tests/unit/extension/test_config.js

# Integration tests (41)
node tests/integration/test_agent_loop.js

# E2E (auto-starts mock MCP + bridge, 14 tests)
python tests/e2e/test_full_cycle.py
```

---

## Tech Stack

- **Extension:** Chrome Manifest V3, vanilla JavaScript, content scripts (MAIN world)
- **Bridge:** Python 3.12, asyncio, websockets 15
- **Protocol:** MCP (Model Context Protocol) over stdio JSON-RPC 2.0
- **Testing:** pytest, Node.js (JS tests), mock MCP server

---

## FAQ

### Which AI platforms work?

DeepSeek, Gemini, Kimi, Z.AI (GLM), Arena, and Qwen. The extension intercepts SSE streams from their chat endpoints.

### Do I need API keys?

No. The extension works with the free web versions of supported platforms.

### Is my code safe?

The SAFE list ensures only read-only and low-risk tools auto-execute. `multi_edit` requires manual approval. `execute_luau` passes through a whitelist that blocks dangerous operations.

### Can I add a new platform?

Create a provider adapter in `extension/providers/`, register it in `manifest.json`, and add the hostname to `net-intercept.js`'s `_H` config.

---

## License

MIT
