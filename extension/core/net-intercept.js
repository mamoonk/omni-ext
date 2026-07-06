(function(){
let _a = window.__ZS_NET;
if (_a && _a._hooked) return; // already injected

// deduplicate streaming chunks: latest fetch accumulates here
let _acc = '', _ts = 0, _active = false, _seq = 0;
const _host = window.location.hostname;

function _cbs() {
  const e = document.body;
  let did = false;
  for (const cb of (_a?._cbs || [])) {
    try { cb(_acc, _ts, _seq, _active, _host); did = true; } catch {}
  }
  return did;
}

// Provider configs keyed by hostname
const _H = {};
function _reg(h, cfg) { _H[h] = cfg; }

_reg('chat.deepseek.com', { ep: '/api/', mode: 'sse', ctx: (j) => j?.choices?.[0]?.delta?.content });
_reg('gemini.google.com',   { ep: '/_/BardChatApi', mode: 'sse' });
_reg('www.kimi.com',       { ep: '/api/', mode: 'sse', ctx: (j) => j?.reply || j?.choices?.[0]?.delta?.content });
_reg('chat.z.ai',          { ep: '/api/', mode: 'sse', ctx: (j) => j?.choices?.[0]?.delta?.content });
_reg('chat.qwen.ai',       { ep: '/api/', mode: 'sse', ctx: (j) => j?.choices?.[0]?.delta?.content });
_reg('arena.ai',           { ep: '/api/', mode: 'sse', ctx: (j) => j?.choices?.[0]?.delta?.content });

// Gemini-specific: parse their nested array response
function _geminiParse(raw) {
  try {
    const j = JSON.parse(raw);
    // Gemini returns [[["text"],[synth]],...] arrays
    const arr = Array.isArray(j) ? j.flat(10) : [];
    for (const v of arr) {
      if (typeof v === 'string' && v.length > 10) return v;
    }
    // fallback: find any long string
    for (const v of arr) {
      if (typeof v === 'string' && v.length > _acc.length) return v;
    }
  } catch {}
  return '';
}

// SSE line reader
async function _readSSE(reader, cfg) {
  const dec = new TextDecoder();
  let buf = '', out = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split('\n');
    buf = parts.pop() || '';
    for (const line of parts) {
      const t = line.trim();
      if (!t.startsWith('data: ')) continue;
      const raw = t.slice(6);
      if (raw === '[DONE]') continue;
      try {
        const j = JSON.parse(raw);
        const c = cfg.ctx ? cfg.ctx(j) : (j?.choices?.[0]?.delta?.content || j?.choices?.[0]?.text || '');
        if (c) out += c;
      } catch {}
    }
  }
  return out;
}

// Hook fetch
const _of = window.fetch;
window.fetch = function(i, init) {
  const url = (typeof i === 'string' ? i : i?.url) || '';
  const cfg = _H[_host];
  if (!cfg || !url.includes(cfg.ep)) {
    return _of.apply(this, arguments);
  }
  _active = true;
  _acc = '';
  const ts0 = Date.now();
  _cbs();
  return _of.apply(this, arguments).then(async (r) => {
    if (!r.ok || !r.body) { _active = false; _cbs(); return r; }
    try {
      const clone = r.clone();
      if (cfg.mode === 'sse') {
        _acc = await _readSSE(clone.body.getReader(), cfg);
      } else {
        _acc = await clone.text();
      }
      // Gemini post-processing
      if (_host === 'gemini.google.com' && cfg.mode === 'sse') {
        _acc = _geminiParse(_acc) || _acc;
      }
    } catch {}
    _ts = Date.now();
    _seq++;
    _active = false;
    _cbs();
    return r;
  });
};

// Also hook XMLHttpRequest for providers that use it
const _oXHR = window.XMLHttpRequest;
window.XMLHttpRequest = function() {
  const x = new _oXHR();
  const cfg = _H[_host];
  if (!cfg) return x;
  const _oS = x.open;
  x.open = function(m, u) {
    if (typeof u === 'string' && u.includes(cfg.ep)) {
      x.___zs = true;
    }
    return _oS.apply(this, arguments);
  };
  const _oRL = x.onreadystatechange;
  x.addEventListener('readystatechange', function() {
    if (x.___zs && x.readyState === 4 && x.status === 200) {
      _active = true;
      _acc = x.responseText || '';
      _ts = Date.now(); _seq++; _active = false;
      _cbs();
    }
  });
  return x;
};

// API for providers to register + read
const api = {
  getText: () => _acc,
  getTs: () => _ts,
  getSeq: () => _seq,
  isActive: () => _active,
  getHost: () => _host,
  onResponse: (cb) => { _a._cbs.push(cb); },
  offResponse: (cb) => { _a._cbs = _a._cbs.filter(c => c !== cb); },
};

// Store on window for isolated world to read
// Use a uniquely-named element to pass the data cross-world
const _el = document.createElement('div');
_el.id = '__zs_net_data';
_el.style.display = 'none';
document.documentElement.appendChild(_el);

function _syncEl() {
  _el.dataset.text = _acc;
  _el.dataset.ts = String(_ts);
  _el.dataset.seq = String(_seq);
  _el.dataset.active = _active ? '1' : '0';
}

// Sync on response
const _origCb = _a?._cbs || [];
_a = window.__ZS_NET = { _hooked: true, ...api, _cbs: [..._origCb, _syncEl] };

// Also expose via DOM attribute synchronously for polling
setInterval(_syncEl, 200);
_syncEl();
})();
