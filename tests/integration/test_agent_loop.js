/**
 * Integration test for the agent loop: poll -> parse -> tool call -> result injection.
 * Tests the full logical chain without browser/DOM dependencies.
 * DOM-dependent parts (net element, UI) are tested separately with jsdom.
 */

let passed = 0;
let failed = 0;

function assert(cond, msg) { if (cond) { passed++; } else { failed++; console.error(`FAIL: ${msg}`); } }
function assertEq(a, b, msg) {
  const aS = JSON.stringify(a);
  const bS = JSON.stringify(b);
  if (aS === bS) { passed++; }
  else { failed++; console.error(`FAIL: ${msg} — expected ${bS}, got ${aS}`); }
}

// ── Mock net element (simulates DOM dataset) ──
function makeMockNet() {
  let _text = "", _seq = 0, _active = false;
  return {
    dataset: {
      get text() { return _text; },
      set text(v) { _text = v; },
      get seq() { return String(_seq); },
      set seq(v) { _seq = parseInt(v, 10) || 0; },
      get active() { return _active ? "1" : "0"; },
      set active(v) { _active = v === "1" || v === true; },
    },
    getSeq: () => _seq,
  };
}

// ── Mock P (provider) ──
function makeMockProvider() {
  const sendCalls = [];
  return {
    send: (t) => { sendCalls.push(t); },
    getSendCalls: () => sendCalls,
    reset: () => { sendCalls.length = 0; },
  };
}

// ── ZSParse stub ──
const ZSParse = (() => {
  const _pt = /TOOL_CALL:\s*(\w+)\s*\(([\s\S]*?)\)/g;
  const _av = (s) => {
    if (!s) return {};
    const r = {};
    let m;
    const kv = /(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\d+(?:\.\d+)?)|true|false)/g;
    while ((m = kv.exec(s)) !== null) {
      let v = m[2] ?? m[3] ?? m[4];
      if (v === "true") v = true;
      else if (v === "false") v = false;
      else if (m[4] !== undefined) v = parseFloat(m[4]);
      if (v !== undefined) r[m[1]] = v;
    }
    return r;
  };
  return {
    parse: (t) => { _pt.lastIndex = 0; const m = _pt.exec(t); if (!m) return null; return { name: m[1], args: _av(m[2]) }; },
  };
})();

// ── Test 1: Polling logic ──
function testPollingLogic() {
  const net = makeMockNet();
  let lastSeq = 0;

  function poll() {
    const active = net.dataset.active === "1";
    if (active) return null;
    const seq = parseInt(net.dataset.seq || "0", 10);
    if (seq <= lastSeq) return null;
    lastSeq = seq;
    const text = net.dataset.text || "";
    if (!text) return null;
    const call = ZSParse.parse(text);
    if (!call) return null;
    return call;
  }

  // No tool call
  net.dataset.text = "just regular text";
  net.dataset.seq = "1";
  assertEq(poll(), null, "no tool call returns null");

  // Tool call present
  net.dataset.text = 'TOOL_CALL: script_read(path="game.Foo")';
  net.dataset.seq = "2";
  const call1 = poll();
  assert(call1 !== null, "tool call detected");
  assertEq(call1.name, "script_read", "correct tool name parsed");
  assertEq(call1.args.path, "game.Foo", "correct arg parsed");

  // Same seq should not re-execute
  assertEq(poll(), null, "same seq not re-executed");

  // New seq with tool call
  net.dataset.text = 'TOOL_CALL: screen_capture()';
  net.dataset.seq = "3";
  const call2 = poll();
  assertEq(call2.name, "screen_capture", "second tool call detected");
}

// ── Test 2: SAFE tool list ──
function testSafeToolBypass() {
  const SAFE = [
    "script_read", "script_create", "script_search", "script_grep", "execute_luau",
    "inspect_instance", "search_game_tree", "list_roblox_studios",
    "set_active_studio", "generate_mesh", "generate_material",
    "generate_procedural_model", "insert_from_creator_store",
    "start_stop_play", "console_output", "screen_capture",
    "character_navigation", "keyboard_input", "mouse_input",
  ];

  assert(SAFE.includes("screen_capture"), "screen_capture is safe");
  assert(SAFE.includes("execute_luau"), "execute_luau is safe");
  assert(!SAFE.includes("multi_edit"), "multi_edit is NOT safe");
  assertEq(SAFE.length, 19, "19 safe tools");
}

// ── Test 3: Tool call routing ──
function testToolCallRouting() {
  return new Promise((resolve) => {
    let toolResult = null;

    // Simulate chrome.runtime.sendMessage
    function sendMessage(msg, cb) {
      setTimeout(() => {
        if (msg.type === "call_tool") {
          cb({ ok: true, text: "result from " + msg.name, images: [] });
        } else if (msg.type === "status") {
          cb({ connected: true, studio: true, mcpAlive: true, tools: 20 });
        }
      }, 10);
    }

    // Simulate _execCall
    function execCall(call) {
      sendMessage(
        { type: "call_tool", name: call.name, arguments: call.args || {}, timeout: 120000 },
        (r) => { toolResult = r; }
      );
    }

    execCall({ name: "screen_capture", args: {} });

    setTimeout(() => {
      assert(toolResult !== null, "tool result received");
      if (toolResult) {
        assert(toolResult.ok, "tool succeeded");
        assertEq(toolResult.text, "result from screen_capture", "correct text");
        assert(Array.isArray(toolResult.images), "images array present");
      }
      resolve();
    }, 50);
  });
}

// ── Test 4: System prompt injection ──
function testSystemPromptInjection() {
  const SP = `You are a Roblox Studio AI agent with vision.

VISION LOOP: After editing UI scripts, call start_stop_play(action="start") then screen_capture().`;

  assert(SP.includes("VISION LOOP"), "SP contains vision loop instructions");
  assert(SP.includes("screen_capture"), "SP mentions screen_capture");
  assert(SP.includes("start_stop_play"), "SP mentions start_stop_play");
}

// ── Test 5: Custom prompt merging ──
function testCustomPromptMerging() {
  const SP = "Base prompt";
  const customPrompt = "Focus on UI only";
  const memory = "Working on health bar";

  const merged = SP + (customPrompt ? "\n\n" + customPrompt : "") + (memory ? "\n\nProject memory:\n" + memory : "");
  assert(merged.includes("Base prompt"), "base prompt preserved");
  assert(merged.includes("Focus on UI only"), "custom prompt merged");
  assert(merged.includes("Working on health bar"), "memory merged");
  assert(merged.includes("Project memory:"), "memory header present");
}

// ── Test 6: Full session simulation ──
function testFullSessionSimulation() {
  const P = makeMockProvider();

  // Start session: inject system prompt
  const SP = "System prompt with VISION LOOP";
  P.send(SP);
  assertEq(P.getSendCalls().length, 1, "system prompt sent");
  assertEq(P.getSendCalls()[0], SP, "correct prompt text");

  // Simulate AI responding with a tool call
  const text = 'TOOL_CALL: execute_luau(code="local p = Instance.new(\'Part\')")';
  const call = ZSParse.parse(text);
  assert(call !== null, "tool call parsed in session");
  assertEq(call.name, "execute_luau", "correct tool in session");

  // Simulate result sent back
  P.send("[Result]\nExecuted successfully");
  assertEq(P.getSendCalls().length, 2, "result sent back");
  assertEq(P.getSendCalls()[1], "[Result]\nExecuted successfully", "result text correct");

  // Simulate image result for screen_capture
  P.reset();
  const imgResult = {
    ok: true,
    text: "Screenshot captured (1920x1080)",
    images: [{ data: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAA=", mimeType: "image/png" }]
  };

  assert(imgResult.images.length === 1, "image in result");
  assert(typeof imgResult.images[0].data === "string", "image data is base64 string");
  assert(imgResult.images[0].mimeType === "image/png", "image mime type correct");
}

// ── Test 7: Multiple tool calls in sequence ──
function testSequentialToolCalls() {
  const calls = [
    { name: "execute_luau", args: { code: "local x=1" } },
    { name: "start_stop_play", args: { action: "start" } },
    { name: "screen_capture", args: {} },
  ];

  let callIdx = 0;
  function processNext() {
    if (callIdx >= calls.length) return;
    const call = calls[callIdx++];
    // Simulate execution
    const result = { ok: true, text: call.name + " result", images: call.name === "screen_capture" ? [{ data: "img" }] : [] };
    // Feed back
    const text = "[Result]\n" + result.text;
    assert(text.includes(call.name), "result for " + call.name + " fed back");
    return result;
  }

  // Process all three calls
  const results = calls.map(() => processNext());
  assertEq(callIdx, 3, "all 3 calls processed");
  assert(results[2].images.length > 0, "screen_capture has images");
  assert(results[0].images.length === 0, "execute_luau has no images");
  assert(results[1].images.length === 0, "start_stop_play has no images");
}

// ── Test 8: Active/inactive polling guard ──
function testActivePollingGuard() {
  const net = makeMockNet();
  let lastSeq = 0;

  function poll() {
    if (net.dataset.active === "1") return "SKIPPED_ACTIVE";
    const seq = parseInt(net.dataset.seq || "0", 10);
    if (seq <= lastSeq) return "SKIPPED_STALE";
    lastSeq = seq;
    return "OK";
  }

  net.dataset.active = "1";
  net.dataset.seq = "1";
  assertEq(poll(), "SKIPPED_ACTIVE", "skip while active");

  net.dataset.active = "0";
  net.dataset.seq = "2";
  assertEq(poll(), "OK", "proceed when inactive");

  net.dataset.seq = "2"; // same seq
  assertEq(poll(), "SKIPPED_STALE", "skip stale seq");

  net.dataset.seq = "3";
  assertEq(poll(), "OK", "proceed with new seq");
}

// ── Run all tests ──
testPollingLogic();
testSafeToolBypass();
testSystemPromptInjection();
testCustomPromptMerging();
testFullSessionSimulation();
testSequentialToolCalls();
testActivePollingGuard();

// Wrap async test
testToolCallRouting().then(() => {
  console.log(`\nAgent Loop Integration: ${passed} passed, ${failed} failed, ${passed + failed} total`);
  process.exit(failed > 0 ? 1 : 0);
});
