const el=s=>document.getElementById(s);
function set(id,text,cls){const e=el(id);if(e){e.textContent=text;e.className='v '+(cls||'gy')}}
function refresh(){
 chrome.runtime.sendMessage({type:"status"},r=>{
  if(!r){set("st-br","No response","r");return}
  set("st-br",r.connected?"Connected":"Offline",r.connected?"g":"r");
  set("st-sa",r.studioApp===true?"Connected":r.studioApp===false?"Disconnected":"?","st-sa",r.studioApp===true?"g":r.studioApp===false?"y":"gy");
  set("st-pl",r.studio===true?"Loaded":r.studio===false?"Not loaded":"?","st-pl",r.studio===true?"g":"y");
  set("st-tl",String(r.tools??0),r.tools>0?"g":"gy");
 });
}
document.getElementById("btn-rc").addEventListener("click",()=>{chrome.runtime.sendMessage({type:"reconnect"});refresh()});
refresh();
setInterval(refresh,5000);
