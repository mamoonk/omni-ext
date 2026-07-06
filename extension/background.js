const P=17613,U=`ws://127.0.0.1:${P}`;
const PU=["https://chat.deepseek.com/*","https://gemini.google.com/*","https://www.kimi.com/*","https://chat.z.ai/*","https://chat.qwen.ai/*","https://arena.ai/*"];
const R1=1000,R2=5000,HB=10000,STALE=25000,TO=130000;
let ws=null,con=false,rd=R1,rt=null,hbt=null,lma=0,nid=1,pd=new Map(),tc=[],ma=false,sc=null,sa=null,sp=false;

function log(...a){console.log("[zs-bg]",...a)}
function c(){
 if(ws&&(ws.readyState===WebSocket.OPEN||ws.readyState===WebSocket.CONNECTING))return;
 clearTimeout(rt);
 try{ws=new WebSocket(U)}catch(e){log("WS fail",e);sch();return}
 ws.onopen=()=>{con=true;rd=R1;lma=Date.now();log("connected");startHB();bcast()};
 ws.onmessage=ev=>{lma=Date.now();let m;try{m=JSON.parse(ev.data)}catch{return};hBM(m)};
 ws.onclose=()=>{con=false;ma=false;sc=null;sa=null;stopHB();failAll("bridge closed");bcast();sch()};
 ws.onerror=()=>{try{ws.close()}catch{}};
}
function sch(){clearTimeout(rt);rt=setTimeout(c,rd);rd=Math.min(rd*1.7,R2)}
function startHB(){stopHB();hbt=setInterval(()=>{if(con){if(lma&&Date.now()-lma>STALE){log("stale");try{ws.close()}catch{}}else snd({type:"ping"}).catch(()=>{});rSS()}},HB)}
function stopHB(){clearInterval(hbt);hbt=null}
function wFC(t=8000){return new Promise(r=>{if(con&&ws&&ws.readyState===WebSocket.OPEN)return r(true);c();const t0=Date.now(),iv=setInterval(()=>{if(con&&ws&&ws.readyState===WebSocket.OPEN){clearInterval(iv);r(true)}else if(Date.now()-t0>t){clearInterval(iv);r(false)}},100)})}
async function snd(obj,t=TO){
 if(!con||!ws||ws.readyState!==WebSocket.OPEN)await wFC(8000);
 return new Promise(r=>{
  if(!con||!ws||ws.readyState!==WebSocket.OPEN){r({ok:false,kind:"disconnected",error:"bridge not connected"});return}
  const id=nid++,pl={...obj,id},tm=setTimeout(()=>{if(pd.has(id)){pd.delete(id);r({ok:false,kind:"timeout",error:"no response"})}},t);
  pd.set(id,{resolve:r,timer:tm});
  try{ws.send(JSON.stringify(pl))}catch(e){clearTimeout(tm);pd.delete(id);r({ok:false,kind:"disconnected",error:String(e)})}
 })}
async function rSS(){if(sp||!con)return;sp=true;try{const r=await snd({type:"studio_status"},12000),v=r&&r.ok&&typeof r.studio==="boolean"?r.studio:null;if(v!==sc){sc=v;bcast()}}finally{sp=false}}
function hBM(m){
 if("studio"in m&&(typeof m.studio==="boolean"||m.studio===null))sc=m.studio;
 if("studio_app"in m&&(typeof m.studio_app==="boolean"||m.studio_app===null))sa=m.studio_app;
 if(m.type==="studio_status"){rP(m.id,{ok:true,studio:sc});bcast();return}
 if(m.type==="connected"){ma=!!m.mcp_alive;if(Array.isArray(m.tools))tc=m.tools;bcast();return}
 if(m.type==="pong"){rP(m.id,{ok:true});return}
 if(m.type==="tools"){if(Array.isArray(m.tools))tc=m.tools;ma=!!msg.mcp_alive;rP(m.id,{ok:true,tools:tc});bcast();return}
 if(m.type==="tool_result"){rP(m.id,m.ok?{ok:true,text:m.text,images:m.images||[]}:{ok:false,kind:m.kind,error:m.error});return}
 if(m.type==="mcp_status"){ma=!!m.alive;rP(m.id,{ok:!!m.ok,alive:m.alive,error:m.error});bcast();return}
 if(m.type==="error"){rP(m.id,{ok:false,error:m.error})}
}
function rP(id,v){const p=pd.get(id);if(!p)return;clearTimeout(p.timer);pd.delete(id);p.resolve(v)}
function failAll(r){for(const[,p]of pd){clearTimeout(p.timer);p.resolve({ok:false,kind:"disconnected",error:r})}pd.clear()}
function sO(){return{type:"zs-status",connected:con,mcpAlive:ma,studio:sc,studioApp:sa,tools:tc.length}}
function bcast(){chrome.runtime.sendMessage(sO()).catch(()=>{});chrome.tabs.query({url:PU},tabs=>{for(const t of tabs)chrome.tabs.sendMessage(t.id,sO()).catch(()=>{})})}
chrome.runtime.onMessage.addListener((msg,sr,srFn)=>{(async()=>{switch(msg.type){case"status":if(!con)c();srFn(sO());break;case"list_tools":{const r=await snd({type:"list_tools"},25000);srFn(r.ok?{ok:true,tools:r.tools}:{ok:tc.length>0,tools:tc,error:r.error});break}case"call_tool":{const t=(msg.timeout||120000)+10000,r=await snd({type:"call_tool",name:msg.name,arguments:msg.arguments,timeout:msg.timeout},t);srFn(r);break}case"restart_mcp":{const r=await snd({type:"restart_mcp"},30000);srFn(r);break}case"reconnect":rd=R1;c();srFn({ok:true});break;default:srFn({ok:false,error:"unknown"})}})();return true});
chrome.runtime.onStartup.addListener(c);chrome.runtime.onInstalled.addListener(c);c();
