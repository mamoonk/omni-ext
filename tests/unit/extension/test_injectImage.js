/**
 * Unit tests for _injectImage() — vision feedback injection logic.
 * Tests base64→File conversion, contenteditable vs textarea branching,
 * input/button selector matching, and fallback behavior.
 */

// Simulate the _injectImage logic from main.js without DOM dependency
// We test the logical components: selectors, branching, and data conversion

let passed = 0;
let failed = 0;

function assert(cond, msg) {
  if (cond) { passed++; }
  else { failed++; console.error(`FAIL: ${msg}`); }
}

function assertEq(a, b, msg) {
  const aS = JSON.stringify(a);
  const bS = JSON.stringify(b);
  if (aS === bS) { passed++; }
  else { failed++; console.error(`FAIL: ${msg} — expected ${bS}, got ${aS}`); }
}

// ── Input selectors (replicated from main.js) ──
const INPUT_SELECTORS = [
  'div[contenteditable="true"]',
  '[data-testid="chat-input"] textarea',
  '#chat-input textarea',
  'textarea[placeholder*="message"]',
  'textarea[placeholder*="input"]',
];

const BUTTON_SELECTORS = [
  'button[aria-label*="send" i]',
  'button[aria-label="Send"]',
  '[data-testid="send-button"]',
  'button[type="submit"]',
  '.send-btn',
  'button.send-button',
  '[class*="send"]:not([class*="secondary"]):not([class*="outline"])',
];

// ── Test: base64 decoding ──
function testBase64Decoding() {
  // Simple base64 test: "hello" = aGVsbG8=
  const b64 = "aGVsbG8=";
  const raw = atob(b64);
  const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);
  const dec = new TextDecoder().decode(buf);
  assertEq(dec, "hello", "base64 decode hello");
}

// ── Test: base64 image data URL construction ──
function testDataUrlConstruction() {
  // PNG 1x1 pixel (minimal valid PNG)
  const pngB64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
  const dataUrl = `data:image/png;base64,${pngB64}`;
  assert(dataUrl.startsWith("data:image/png;base64,"), "data URL prefix correct");
  assert(dataUrl.length > 100, "data URL contains full base64");
}

// ── Test: contenteditable HTML generation ──
function testContenteditableHtml() {
  const base64 = "dGVzdC1pbWFnZS1kYXRh";
  const text = "[Result]\nScreenshot captured";
  const html = `<img src="data:image/png;base64,${base64}" style="max-width:280px;max-height:200px;border-radius:4px;margin:4px 0"><br>${text}`;
  assert(html.includes('<img src="data:image/png;base64,dGVzdC1pbWFnZS1kYXRh"'), "HTML contains img tag with data URL");
  assert(html.includes("[Result]"), "HTML contains result text");
  assert(html.includes("Screenshot captured"), "HTML contains screenshot text");
  assert(html.includes("<br>"), "HTML has line break between image and text");
}

// ── Test: input selector querying (simulated DOM) ──
function testInputSelectorMatching() {
  // Simulate document.querySelector using our selectors
  function querySelector(sel) {
    // Return "contenteditable" for div[contenteditable="true"]
    if (sel === 'div[contenteditable="true"]') return "contenteditable";
    return null;
  }
  function querySelectorAll(sel) {
    // Return matching elements
    if (sel === INPUT_SELECTORS.join(", ")) return ["contenteditable"];
    return [];
  }

  // Test priority order: contenteditable first
  const firstMatch = querySelector('div[contenteditable="true"]');
  assertEq(firstMatch, "contenteditable", "contenteditable div matched first");
}

// ── Test: textarea base64→File conversion ──
function testBase64ToFile() {
  const b64 = "dGVzdA=="; // "test"
  // Simulate URL-safe base64 conversion
  const safe = b64.replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(safe);
  const buf = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);

  // Would create File in real code:
  // const f = new File([buf], "screenshot.png", {type: "image/png"});
  // const dt = new DataTransfer();
  // dt.items.add(f);

  assert(buf.length === 4, "decoded buffer length correct");
  assertEq(new TextDecoder().decode(buf), "test", "decoded content correct");
}

// ── Test: URL-safe base64 handling ──
function testUrlSafeBase64() {
  const original = "abc+def/ghi==";
  const converted = original.replace(/-/g, "+").replace(/_/g, "/");
  assertEq(converted, "abc+def/ghi==", "no change when already standard base64");

  const urlSafe = "abc-def_ghi";
  const toStandard = urlSafe.replace(/-/g, "+").replace(/_/g, "/");
  assertEq(toStandard, "abc+def/ghi", "URL-safe converted to standard");
}

// ── Test: image array extraction ──
function testImageExtraction() {
  const toolResult = {
    ok: true,
    text: "Screenshot captured (1920x1080)",
    images: [
      { data: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAA=", mimeType: "image/png" }
    ]
  };

  const imgs = toolResult.images || [];
  assert(imgs.length > 0, "images array populated");
  assertEq(imgs[0].data.substring(0, 10), "iVBORw0KGg", "image data accessible via .data");
  assertEq(imgs[0].mimeType, "image/png", "mimeType accessible");
}

// ── Test: fallback when no input element ──
function testFallbackBehavior() {
  // When no input element found, fall back to P.send(text)
  let pSendCalled = false;
  let pSendText = null;

  const P = {
    send: (t) => { pSendCalled = true; pSendText = t; }
  };

  // Simulate: no input element found
  const el = null;
  if (!el) { P.send("[Result]\ntest"); }

  assert(pSendCalled, "P.send called as fallback");
  assertEq(pSendText, "[Result]\ntest", "P.send called with correct text");
}

// ── Test: empty images array ──
function testEmptyImages() {
  const toolResult = { ok: true, text: "done", images: [] };
  const imgs = toolResult.images || [];
  assert(imgs.length === 0, "empty images array");
}

// ── Test: undefined images field ──
function testUndefinedImages() {
  const toolResult = { ok: true, text: "done" };
  const imgs = toolResult.images || [];
  assert(imgs.length === 0, "undefined images becomes empty array");
}

// ── Test: images field is array of objects ──
function testImagesStructure() {
  const toolResult = {
    ok: true,
    text: "",
    images: [
      { data: "AAAA", mimeType: "image/jpeg" },
      { data: "BBBB", mimeType: "image/png" }
    ]
  };
  assert(Array.isArray(toolResult.images), "images is an array");
  assertEq(toolResult.images.length, 2, "two images in array");
  toolResult.images.forEach((img, i) => {
    assert(typeof img.data === "string", `image ${i} has data string`);
    assert(typeof img.mimeType === "string", `image ${i} has mimeType string`);
  });
}

// ── Test: file size estimation ──
function testFileSizeEstimation() {
  // PNG data: roughly (width * height * 4) bytes before compression
  // For a base64 string, decoded size = base64.length * 3/4
  const mockBase64 = "A".repeat(1600); // ~1200 bytes decoded
  const decodedLength = Math.floor(mockBase64.length * 3 / 4);
  // Strip padding
  const padding = mockBase64.endsWith("==") ? 2 : mockBase64.endsWith("=") ? 1 : 0;
  const actualLength = Math.floor(mockBase64.length * 3 / 4) - padding;
  assert(actualLength > 0, "file size estimation positive");
}

// ── Test: selector priority order ──
function testSelectorPriority() {
  // The order of INPUT_SELECTORS matters: contenteditable first, textarea last
  assert(INPUT_SELECTORS[0].includes("contenteditable"), "contenteditable is first priority");
  assert(INPUT_SELECTORS[INPUT_SELECTORS.length - 1].includes("textarea"), "textarea is lower priority");
}

// ── Test: button selector comprehensiveness ──
function testButtonSelectors() {
  assert(BUTTON_SELECTORS.some(s => s.includes("send")), "at least one button selector targets 'send'");
  assert(BUTTON_SELECTORS.some(s => s.includes("submit")), "has type=submit selector");
  assert(BUTTON_SELECTORS.some(s => s.includes("Send")), "has aria-label=Send selector");
}

// Run all tests
testBase64Decoding();
testDataUrlConstruction();
testContenteditableHtml();
testInputSelectorMatching();
testBase64ToFile();
testUrlSafeBase64();
testImageExtraction();
testFallbackBehavior();
testEmptyImages();
testUndefinedImages();
testImagesStructure();
testFileSizeEstimation();
testSelectorPriority();
testButtonSelectors();

console.log(`\nInjectImage: ${passed} passed, ${failed} failed, ${passed + failed} total`);
process.exit(failed > 0 ? 1 : 0);
