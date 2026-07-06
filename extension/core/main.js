(function(){
let S={active:false,stopping:false,run:false,customPrompt:"",memory:"",_lastSeq:0,_queue:[]};
const SAFE=['script_read','script_create','script_search','script_grep','execute_luau','inspect_instance','search_game_tree','list_roblox_studios','set_active_studio','generate_mesh','generate_material','generate_procedural_model','insert_from_creator_store','start_stop_play','console_output','screen_capture','character_navigation','keyboard_input','mouse_input'];

function id(n){return `zs-${n}`}

// ── UI (bar) ──
let bar=null,stDot=null,stLbl=null,btn=null;
function buildUI(){
 if(bar)return;
 bar=document.createElement("div");bar.id=id("bar");bar.style.cssText="position:fixed;top:0;left:0;right:0;z-index:99999;background:#1a1a2e;color:#eee;padding:4px 12px;font:13px/1.4 sans-serif;display:flex;align-items:center;gap:8px;box-shadow:0 2px 8px rgba(0,0,0,.4);height:36px";
 const logo=document.createElement("span");logo.textContent="Omni-Ext";logo.style.cssText="font-weight:700;color:#7c5cfc;margin-right:8px";
 stDot=document.createElement("span");stDot.textContent="●";stDot.style.cssText="font-size:16px;color:#666;margin-right:4px";
 stLbl=document.createElement("span");stLbl.textContent="Bridge offline";stLbl.style.cssText="color:#999;font-size:12px";
 btn=document.createElement("button");btn.id=id("toggle");btn.textContent="▶ Start";btn.style.cssText="margin-left:auto;padding:3px 12px;border:1px solid #7c5cfc;border-radius:4px;background:transparent;color:#7c5cfc;cursor:pointer;font-size:12px";
 btn.onmouseover=()=>btn.style.background="#7c5cfc33";
 btn.onmouseout=()=>btn.style.background="transparent";
 const more=document.createElement("button");more.textContent="⚙";more.className="zs-btn";more.title="Custom instructions";
 const memo=document.createElement("button");memo.textContent="📝";memo.className="zs-btn";memo.title="Project memory";
 [logo,stDot,stLbl,memo,more,btn].forEach(el=>bar.appendChild(el));
 document.body.prepend(bar);
 document.body.style.paddingTop="44px";
 btn.addEventListener("click",()=>S.active?stopSession():startSession());
  more.addEventListener("click",()=>{const p=prompt("Custom instructions:",S.customPrompt);if(p!==null){S.customPrompt=p;try{chrome.storage.local.set({zsp:S.customPrompt,zsm:S.memory})}catch{}}});
  memo.addEventListener("click",()=>{const p=prompt("Project memory:",S.memory);if(p!==null){S.memory=p;try{chrome.storage.local.set({zsp:S.customPrompt,zsm:S.memory})}catch{}}});
}
function setStatus(dot,label){if(stDot)stDot.style.color=dot;if(stLbl)stLbl.textContent=label}
function setBtn(text,active){if(!btn)return;btn.textContent=text;btn.style.borderColor=active?"#ff5555":"#7c5cfc";btn.style.color=active?"#ff5555":"#7c5cfc"}

// ── Diff modal ──
let modal=null;
function _ensureModal(){
 if(modal)return;
 modal=document.createElement("div");modal.id=id("modal");modal.style.cssText="display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:999999;background:rgba(0,0,0,.7);justify-content:center;align-items:flex-start;padding:60px 20px;overflow-y:auto";
 const c=document.createElement("div");c.id=id("modal-content");c.style.cssText="background:#1a1a2e;color:#eee;border-radius:8px;max-width:800px;width:100%;padding:20px;font:13px/1.4 monospace;box-shadow:0 8px 32px rgba(0,0,0,.5);max-height:80vh;overflow-y:auto";
 modal.appendChild(c);
 document.body.appendChild(modal);
}
function _modalShow(html){
 _ensureModal();
 const c=document.getElementById(id("modal-content"));c.innerHTML=html;
 modal.style.display="flex";
 return new Promise(r=>{
  c.querySelector('.zs-approve')?.addEventListener('click',()=>{modal.style.display="none";r('approve')});
  c.querySelector('.zs-reject')?.addEventListener('click',()=>{modal.style.display="none";r('reject')});
  c.querySelectorAll('.zs-diff-toggle').forEach(el=>el.addEventListener('click',function(){
   const t=this.nextElementSibling;
   if(t)t.style.display=t.style.display==='none'?'block':'none';
   this.textContent=t?.style.display==='block'?'▼ Hide diff':'▶ View diff';
  }));
 });
}
function _buildDiffHtml(oldLines,edits,path){
 const newLines=[...oldLines];
 for(const e of edits.sort((a,b)=>a.line-b.line)){
  const idx=e.line-1;
  if(idx>=0&&idx<newLines.length)newLines[idx]=e.text;
  else if(idx===newLines.length)newLines.push(e.text);
 }
 // find changed lines
 const changes=[];
 for(let i=0;i<Math.max(oldLines.length,newLines.length);i++){
  if(oldLines[i]!==newLines[i])changes.push({line:i+1,old:oldLines[i]||'',new:newLines[i]||''});
 }
 return `<div style="margin-bottom:10px"><strong style="color:#7c5cfc">${path}</strong> — ${changes.length} change(s)</div>
<div style="background:#0d0d1a;padding:8px;border-radius:4px;max-height:300px;overflow-y:auto;font-size:12px;line-height:1.5;white-space:pre-wrap;font-family:monospace">
${changes.map(c=>`<div style="color:#888;border-bottom:1px solid #222">${c.line}</div><div style="color:#f55;background:#2d1111">- ${_esc(c.old)}</div><div style="color:#5f5;background:#112d11">+ ${_esc(c.new)}</div>`).join('')}
</div>`;
}
function _esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

async function _approveMultiEdit(call){
 setStatus("#fa0","Requesting approval...");
 // read current script content
 const r=await new Promise(r=>chrome.runtime.sendMessage({type:"call_tool",name:"script_read",arguments:{path:call.args.path},timeout:30000},r));
 if(S.stopping)return null;
 const oldContent=(r?.ok?r.text:'')||'';
 const oldLines=oldContent.split('\n');
 const edits=Array.isArray(call.args.edits)?call.args.edits:[];
 const html=`<div style="margin-bottom:16px;font-size:15px;color:#7c5cfc;font-weight:700">AI wants to modify <span style="color:#eee">${edits.length}</span> edit(s) in <span style="color:#eee">${_esc(call.args.path)}</span></div>
${edits.length<=10?_buildDiffHtml(oldLines,edits,call.args.path):`<div style="color:#fa0;margin-bottom:8px">Showing summary only (${edits.length} edits — too many for inline diff)</div>
${edits.map(e=>`<div style="padding:2px 0;color:#aaa;border-bottom:1px solid #222">Line ${e.line}: <span style="color:#eee">${_esc((e.text||'').slice(0,80))}</span></div>`).join('')}`}
<div style="margin-top:16px;display:flex;gap:10px;justify-content:flex-end">
<button class="zs-reject" style="padding:6px 20px;border:1px solid #f55;border-radius:4px;background:transparent;color:#f55;cursor:pointer;font-size:13px">Reject</button>
<button class="zs-approve" style="padding:6px 20px;border:1px solid #5f5;border-radius:4px;background:transparent;color:#5f5;cursor:pointer;font-size:13px">Approve</button>
</div>`;
 const decision=await _modalShow(html);
 if(decision==='reject')return null;
 return call.args; // approved, return args unchanged
}

// ── Net read ──
function _netEl(){return document.getElementById("__zs_net_data")}
function _netText(){const e=_netEl();return e?.dataset?.text||""}
function _netSeq(){const e=_netEl();return parseInt(e?.dataset?.seq||"0",10)}
function _netActive(){const e=_netEl();return e?.dataset?.active==="1"}

// ── Agent loop ──
let loopTimer=null,pollTimer=null;
async function startSession(){
 if(!P||!P.send){setStatus("#fa0","No provider ready");return}
 S.active=true;S.stopping=false;S.run=true;S._lastSeq=_netSeq();
 setBtn("■ Stop",true);
 const sp=ZS.SP+(S.customPrompt?"\n\n"+S.customPrompt:"")+(S.memory?"\n\nProject memory:\n"+S.memory:"");
 P.send(sp);
 setTimeout(()=>startPoll(),2000);
}
function stopSession(){
 S.stopping=true;S.active=false;S.run=false;
 setBtn("▶ Start",false);setStatus("#666","Stopped");
 if(loopTimer){clearTimeout(loopTimer);loopTimer=null}
 if(pollTimer){clearInterval(pollTimer);pollTimer=null}
}
function startPoll(){if(pollTimer)return;pollTimer=setInterval(poll,300)}

// ── Image injection for vision feedback ──
function _injectImage(base64,text){
 const inputSel=[
  'div[contenteditable="true"]',
  '[data-testid="chat-input"] textarea',
  '#chat-input textarea',
  'textarea[placeholder*="message"]',
  'textarea[placeholder*="input"]',
 ].join(', ');
 const btnSel=[
  'button[aria-label*="send" i]',
  'button[aria-label="Send"]',
  '[data-testid="send-button"]',
  'button[type="submit"]',
  '.send-btn',
  'button.send-button',
  '[class*="send"]:not([class*="secondary"]):not([class*="outline"])',
 ].join(', ');
 const el=document.querySelector(inputSel);
 if(!el){P.send(text);return}
 el.focus();
 if(el.isContentEditable){
  document.execCommand('insertHTML',false,
   `<img src="data:image/png;base64,${base64}" style="max-width:280px;max-height:200px;border-radius:4px;margin:4px 0"><br>`+text);
  }else{
   try{
    const b64=base64.replace(/-/g,'+').replace(/_/g,'/');
    const raw=atob(b64);
    const buf=new Uint8Array(raw.length);
    for(let i=0;i<raw.length;i++)buf[i]=raw.charCodeAt(i);
    const f=new File([buf],'screenshot.png',{type:'image/png'}),dt=new DataTransfer();
    dt.items.add(f);
    el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}));
    document.execCommand('insertText',false,'\n'+text);
   }catch(e){
    // textarea fallback: embed as markdown image
    document.execCommand('insertText',false,`\n![screenshot](data:image/png;base64,${base64})\n`+text);
   }
  }
 const btn=document.querySelector(btnSel);
 if(btn)setTimeout(()=>btn.click(),150);
}

async function _execCall(call){
 const isEdit=call.name==='multi_edit';
 let args=call.args;
 if(isEdit){
  args=await _approveMultiEdit(call);
  if(!args){setStatus("#0c0","Skipped (rejected)");_processQueue();return}
 }
 setStatus("#7c5cfc",`${isEdit?'[APPROVED] ':''}Running ${call.name}...`);
 chrome.runtime.sendMessage({type:"call_tool",name:call.name,arguments:args,timeout:120000},r=>{
  if(S.stopping)return;
  const rt=r?.ok?(r.text||"(no output)"):("Error: "+r?.error);
  const imgs=r?.images||[];
  if(imgs.length>0)_injectImage(imgs[0].data||imgs[0],"[Result]\n"+rt);
  else P.send("[Result]\n"+rt);
  setStatus("#0c0","Agent running");
  _processQueue();
 });
}
function _processQueue(){
 _isProcessing=false;
 if(S._queue.length===0)return;
 const call=S._queue.shift();
 if(SAFE.includes(call.name)||call.name==='multi_edit'){_isProcessing=true;_execCall(call)}
 else{setStatus("#f55",`Blocked: ${call.name} not in SAFE`);_processQueue()}
}

function poll(){
 if(!S.run||S.stopping)return;
 const active=_netActive();
 if(active)return;
 const seq=_netSeq();
 if(seq<=S._lastSeq)return;
 S._lastSeq=seq;
 const text=_netText();
 if(!text)return;
 const call=ZSParse.parse(text);
 if(!call)return;
 if(!SAFE.includes(call.name)&&call.name!=='multi_edit'){setStatus("#f55",`Blocked: ${call.name} not in SAFE`);return}
 if(_isProcessing){S._queue.push(call);return}
 _isProcessing=true;
 _execCall(call);
}
let _isProcessing=false;

// ── Status ──
chrome.runtime.onMessage.addListener(msg=>{
 if(msg.type!=="zs-status")return;
 if(!msg.connected)setStatus("#666","Bridge offline");
 else if(!msg.studio)setStatus("#fa0","Studio not ready");
 else setStatus("#0c0","Ready");
});
chrome.runtime.sendMessage({type:"status"},r=>{
 if(!r)return;
 if(!r.connected)setStatus("#666","Bridge offline");
 else if(!r.studio)setStatus("#fa0","Studio not ready");
 else setStatus("#0c0","Ready");
});

buildUI();
var P=typeof ZSProvider!=="undefined"?ZSProvider:null;
try{chrome.storage.local.get(['zsp','zsm'],r=>{if(r){if(r.zsp)S.customPrompt=r.zsp;if(r.zsm)S.memory=r.zsm}})}catch{}
})();
