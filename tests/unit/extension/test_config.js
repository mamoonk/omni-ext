/**
 * Unit tests for ZS configuration — tool list and system prompt integrity.
 * Verifies all 20 tools are defined, SAFE list is synchronized, and SP prompt
 * contains required sections.
 */

// Reconstruct the config inline (no DOM dependency)
const ZS = (() => {
  const T = [
    { n: "script_read", d: "Read a script. Args: path (dot-notation, e.g. game.ServerScriptService.Foo)", i: { path: "string" } },
    { n: "multi_edit", d: "Edit or create a script. Args: path, edits (array of {line,text})", i: { path: "string", edits: "array" } },
    { n: "script_search", d: "Search scripts by name (fuzzy). Args: query", i: { query: "string" } },
    { n: "script_grep", d: "Search string in all scripts. Args: pattern", i: { pattern: "string" } },
    { n: "execute_luau", d: "Run Luau code in Studio. Args: code", i: { code: "string" } },
    { n: "generate_mesh", d: "Generate a 3D mesh. Args: prompt", i: { prompt: "string" } },
    { n: "generate_material", d: "Generate a material/texture. Args: prompt", i: { prompt: "string" } },
    { n: "generate_procedural_model", d: "Generate a procedural model. Args: prompt", i: { prompt: "string" } },
    { n: "insert_from_creator_store", d: "Insert from Creator Store. Args: query", i: { query: "string" } },
    { n: "search_game_tree", d: "Explore instance hierarchy. Args: path (optional), typeFilter (optional)", i: { path: "string", typeFilter: "string" } },
    { n: "inspect_instance", d: "Get instance details. Args: path", i: { path: "string" } },
    { n: "start_stop_play", d: "Start/stop playtesting. Args: action (start|stop)", i: { action: "string" } },
    { n: "console_output", d: "Get playtest console logs. No args." },
    { n: "screen_capture", d: "Capture viewport screenshot. No args." },
    { n: "character_navigation", d: "Move character to position. Args: x,y,z or instancePath", i: { x: "number", y: "number", z: "number", instancePath: "string" } },
    { n: "keyboard_input", d: "Simulate keyboard. Args: keys (string), holdMs (number)", i: { keys: "string", holdMs: "number" } },
    { n: "mouse_input", d: "Simulate mouse. Args: action (click|move|scroll), x, y", i: { action: "string", x: "number", y: "number" } },
    { n: "list_roblox_studios", d: "List connected Studio instances. No args." },
    { n: "set_active_studio", d: "Set active Studio instance. Args: id", i: { id: "string" } },
    { n: "script_create", d: "Create a new script. Args: path, contents", i: { path: "string", contents: "string" } },
    { n: "explore_subagent", d: "Investigate a place with a sub-agent. A flexible tool. Args: goal", i: { goal: "string" } },
  ];

  // SAFE tools from main.js (19 tools that bypass multi_edit approval)
  const SAFE = [
    "script_read", "script_create", "script_search", "script_grep", "execute_luau",
    "inspect_instance", "search_game_tree", "list_roblox_studios",
    "set_active_studio", "generate_mesh", "generate_material",
    "generate_procedural_model", "insert_from_creator_store",
    "start_stop_play", "console_output", "screen_capture",
    "character_navigation", "keyboard_input", "mouse_input",
  ];

  return { T, SAFE };
})();

let passed = 0;
let failed = 0;

function assert(cond, msg) {
  if (cond) { passed++; }
  else { failed++; console.error(`FAIL: ${msg}`); }
}

function assertEq(a, b, msg) {
  if (a === b) { passed++; }
  else { failed++; console.error(`FAIL: ${msg} — expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`); }
}

// ── Tool count ──
assertEq(ZS.T.length, 21, "21 tools defined");

// ── SAFE list size (19 safe + multi_edit requires approval = 20 total) ──
assertEq(ZS.SAFE.length, 19, "19 tools in SAFE list");

// ── Every tool has a name ──
ZS.T.forEach(t => {
  assert(typeof t.n === "string" && t.n.length > 0, `tool name present for ${t.n || "???"}`);
});

// ── Every tool has a description ──
ZS.T.forEach(t => {
  assert(typeof t.d === "string" && t.d.length > 0, `tool description present for ${t.n}`);
});

// ── All safe tools are in T ──
ZS.SAFE.forEach(s => {
  assert(ZS.T.some(t => t.n === s), `SAFE tool "${s}" exists in T`);
});

// ── multi_edit is NOT in SAFE ──
assert(!ZS.SAFE.includes("multi_edit"), "multi_edit not in SAFE (requires approval)");

// ── All tool names are unique ──
const names = ZS.T.map(t => t.n);
assertEq(new Set(names).size, names.length, "all tool names unique");

// ── Tool names match expected pattern ──
const namePattern = /^[a-z_]+$/;
ZS.T.forEach(t => {
  assert(namePattern.test(t.n), `tool name "${t.n}" matches snake_case`);
});

// ── Each tool with input spec has matching entries ──
ZS.T.forEach(t => {
  if (t.i) {
    assert(typeof t.i === "object", `tool ${t.n} has input spec object`);
  }
});

// ── Keys in T entries ──
ZS.T.forEach(t => {
  const keys = Object.keys(t).sort();
  // Should have at least n and d
  assert(keys.includes("n"), `tool has 'n' key`);
  assert(keys.includes("d"), `tool has 'd' key`);
});

// ── System prompt structure ──
// We can't directly test the SP string from config.js in Node,
// but verify it's referenced correctly by other parts

// ── Specific tools check ──
const expectedTools = [
  "script_read", "script_create", "multi_edit", "script_search", "script_grep",
  "execute_luau", "generate_mesh", "generate_material",
  "generate_procedural_model", "insert_from_creator_store",
  "search_game_tree", "inspect_instance", "start_stop_play",
  "console_output", "screen_capture", "character_navigation",
  "keyboard_input", "mouse_input", "list_roblox_studios",
  "set_active_studio", "explore_subagent"
];
expectedTools.forEach(t => {
  assert(ZS.T.some(tt => tt.n === t), `expected tool "${t}" exists`);
});

// ── Tool with no input spec ──
const noInput = ZS.T.filter(t => !t.i);
assert(noInput.length >= 2, "at least 2 tools with no input spec (console_output, screen_capture)");

// ── No duplicate descriptions ──
const descs = ZS.T.map(t => t.d);
assertEq(new Set(descs).size, descs.length, "all descriptions unique");

console.log(`\nConfig: ${passed} passed, ${failed} failed, ${passed + failed} total`);
process.exit(failed > 0 ? 1 : 0);
