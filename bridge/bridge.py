import asyncio, json, os, queue, re, subprocess, sys, threading, time, ctypes
try: import websockets
except ImportError: print("[bridge] pip install websockets"); sys.exit(1)

HOST,PORT="127.0.0.1",int(os.environ.get("ZS_BRIDGE_PORT","17613"))
HERE=os.path.dirname(os.path.abspath(__file__))
CFG=os.path.join(HERE,"config.json")
LOG_DIR=os.path.join(HERE,"logs")
os.makedirs(LOG_DIR,exist_ok=True)
LF=None
try: LF=open(os.path.join(LOG_DIR,"bridge_debug.log"),"a",encoding="utf-8",errors="replace")
except: pass
STUDIO_MCP_PORT=13469
NO_PLACE=("doesn't have a place","no place opened","place opened","has disconnected","no active studio")
_DROP=("no roblox studio instance","no active studio","studio instance is connect","studio instance connected","not connected to","no studio instance")

def _log(m,c="",t=True):
 ts=time.strftime("%H:%M:%S")
 if t: print(f"\033[{c}m{ts} {m}\033[0m" if c else f"{ts} {m}",flush=True)
 if LF:
  try: LF.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}\n"); LF.flush()
  except: pass

def _ea():
 if sys.platform!="win32": return True
 try:
  h=ctypes.windll.kernel32.GetStdHandle(-11);m=ctypes.c_uint32()
  return bool(ctypes.windll.kernel32.GetConsoleMode(h,ctypes.byref(m)) and ctypes.windll.kernel32.SetConsoleMode(h,m.value|0x0004))
 except: return False

if not _ea(): _log= lambda m,c="",t=True: (print(f"{time.strftime('%H:%M:%S')} {m}",flush=True) if t else None) or (LF.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {m}\n") and LF.flush() if LF else None)

def _po(p):
 if sys.platform!="win32": return None
 try:
  o=subprocess.run(["netstat","-ano","-p","TCP"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=8).stdout
 except: return None
 pid=None
 for l in o.splitlines():
  if "LISTENING" in l and f":{p} " in l:
   ps=l.split()
   if ps and ps[-1].isdigit(): pid=ps[-1]; break
 if not pid: return None
 n,ph="?",""
 try:
  po=subprocess.run(["powershell","-NoProfile","-Command",f"$p=Get-Process -Id {pid} -ErrorAction SilentlyContinue;if($p){{$p.Name;$p.Path}}"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=8).stdout.splitlines()
  po=[l.strip() for l in po if l.strip()]
  if po: n=po[0]; ph=po[1] if len(po)>1 else ""
 except: pass
 return (pid,n,ph)

def _check_sp():
 o=_po(STUDIO_MCP_PORT)
 if not o: return False
 pid,n,ph=o
 if "roblox" in (ph or "").lower(): return False
 _log(f"port {STUDIO_MCP_PORT} held by non-Roblox: {n} pid {pid}","93")
 try: a=input("Kill it? [y/N] ").strip().lower() in ("y","yes")
 except: a=False
 if a:
  try: subprocess.run(["taskkill","/F","/PID",str(pid)],capture_output=True,text=True,timeout=8); _log("killed","96"); return True
  except: _log("kill failed","91")
 return False

class MCPC:
 def __init__(s,i,c,a,e=None):
  s.id=i;s.cmd=c;s.args=list(a or []);s.env=e or {};s.proc=None;s.rid=1
  s.wl=threading.Lock();s.cl=threading.Lock();s.pd={};s.pl=threading.Lock();s.tc=[];s.sl=threading.Lock();s._rt=None
 def _rs(s,p): return os.path.expandvars(os.path.expanduser(str(p)))
 def start(s):
  with s.sl:
   if s.is_a(): return
   cmd=[s._rs(s.cmd)]+[s._rs(a) for a in s.args]
   if cmd[0].lower().endswith(".py"):
    sp=cmd[0]
    if not os.path.isabs(sp): sp=os.path.join(HERE,sp)
    cmd=[sys.executable,sp]+cmd[1:]
   if sys.platform=="win32" and os.path.basename(cmd[0]).lower() in ("npx","npm","yarn","pnpm","bunx"): cmd=["cmd.exe","/c"]+cmd
   env=dict(os.environ)
   for k,v in s.env.items(): env[k]=s._rs(v)
   _log(f"[{s.id}] launch ({' '.join(cmd)})","96")
   s.proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,encoding="utf-8",errors="replace",cwd=HERE,env=env)
   with s.pl: s.pd.clear()
   s._rt=threading.Thread(target=s._rd,args=(s.proc,),daemon=True); s._rt.start()
   threading.Thread(target=s._sed,args=(s.proc,),daemon=True).start()
   s._rq("initialize",{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"zs-bridge","version":"1.0"}},30)
   s._nf("notifications/initialized")
   for _ in range(12):
    if s.rf_t(3): break
    if not s.is_a(): break
    time.sleep(1)
   _log(f"[{s.id}] up ({len(s.tc)} tools)","96")
 def is_a(s): return s.proc and s.proc.poll() is None
 def rst(s):
  _log(f"[{s.id}] restart","93"); s.stp(); time.sleep(0.4); s.start()
 def stp(s):
  with s.pl:
   for q in s.pd.values():
    try: q.put_nowait(None)
    except: pass
   s.pd.clear()
  if s.proc:
   try:
    if sys.platform=="win32": subprocess.run(["taskkill","/F","/T","/PID",str(s.proc.pid)],capture_output=True,timeout=8)
    else: s.proc.terminate()
   except: pass
   s.proc=None
 def _rd(s,p):
  for l in iter(p.stdout.readline,""):
   if l=="": break
   l=l.strip()
   if not l: continue
   try: m=json.loads(l)
   except: continue
   mid=m.get("id")
   if mid is None: continue
   with s.pl: q=s.pd.get(mid)
   if q:
    try: q.put_nowait(m)
    except: pass
  _log(f"[{s.id}] stdout EOF (exit {p.poll()})","91")
  with s.pl:
   for q in s.pd.values():
    try: q.put_nowait(None)
    except: pass
 def _sed(s,p):
  try:
   for l in iter(p.stderr.readline,""):
    l=l.rstrip()
    if l: _log(f"[{s.id}] stderr: {l}","93",t=False)
  except: pass
 def _nid(s):
  with s.wl: r=s.rid; s.rid+=1; return r
 def _nf(s,m,p=None):
  pl=json.dumps({"jsonrpc":"2.0","method":m,"params":p or {}})
  with s.wl: s.proc.stdin.write(pl+"\n"); s.proc.stdin.flush()
 def _rq(s,m,p,t):
  if not s.is_a(): raise RuntimeError(f"server dead")
  rid=s._nid(); q=queue.Queue(maxsize=1)
  with s.pl: s.pd[rid]=q
  try:
   pl=json.dumps({"jsonrpc":"2.0","id":rid,"method":m,"params":p or {}})
   with s.wl: s.proc.stdin.write(pl+"\n"); s.proc.stdin.flush()
   try: return q.get(timeout=t)
   except queue.Empty: return None
  finally:
   with s.pl: s.pd.pop(rid,None)
 def rf_t(s,t=20):
  m=s._rq("tools/list",{},t)
  if m and "result" in m: s.tc=m["result"].get("tools",[])
  return s.tc
 def cl_t(s,n,a,t):
  with s.cl:
   for at in (1,2):
    if not s.is_a(): s.rst()
    m=s._rq("tools/call",{"name":n,"arguments":a},t)
    if m is None:
     if not s.is_a(): s.rst(); m=s._rq("tools/call",{"name":n,"arguments":a},t)
     if m is None: raise TimeoutError("no response")
    if m.get("error"):
     e=m["error"].get("message",json.dumps(m["error"]))
     if at==1 and any(d in e.lower() for d in _DROP): _log(f"[{s.id}] {n}: transient drop, retry","93"); time.sleep(1.5); continue
     raise RuntimeError(e)
    c=m.get("result",{}).get("content",[])
    tx="\n".join(it.get("text","") for it in c if it.get("type")=="text")
    im=[{"data":it["data"],"mimeType":it.get("mimeType","image/jpeg")} for it in c if it.get("type")=="image" and it.get("data")]
    if not tx and not im and c: tx=json.dumps(c)[:4000]
    if at==1 and any(d in (tx or "").lower() for d in _DROP): _log(f"[{s.id}] {n}: transient drop, retry","93"); time.sleep(1.5); continue
    return {"text":tx,"images":im}

class MCPM:
 def __init__(s):
  s.cl={};s.idx={};s.ixl=threading.Lock()
 def ld_cfg(s):
  sv={}
  if os.path.exists(CFG):
   try:
    with open(CFG,encoding="utf-8") as f: sv=json.load(f).get("mcpServers",{}) or {}
   except Exception as e: _log(f"config error: {e}","91")
  for sid,sp in sv.items(): s.cl[sid]=MCPC(sid,sp.get("command"),sp.get("args"),sp.get("env"))
  _log(f"configured {len(s.cl)} server(s): {', '.join(s.cl) or '(none)'}","96")
 def start_all(s):
  for sid,c in s.cl.items():
   try: c.start()
   except Exception as e: _log(f"[{sid}] start fail: {e}","91")
  s._rbi()
 def _rbi(s):
  with s.ixl:
   s.idx={}
   for sid,c in s.cl.items():
    for t in (c.tc or []):
     n=t.get("name")
     if not n: continue
     a=n if n not in s.idx else f"{sid}/{n}"
     s.idx[a]=(c,n)
 def lt(s,rf=False):
  if rf:
   for sid,c in s.cl.items():
    try:
     if not c.is_a(): c.start()
     else: c.rf_t()
    except: pass
   s._rbi()
  o=[]
  for sid,c in s.cl.items():
   for t in (c.tc or []):
    n=t.get("name"); a=n
    with s.ixl:
     for k,(h,rn) in s.idx.items():
      if h is c and rn==n: a=k; break
    tt=dict(t); tt["name"]=a; o.append(tt)
  return o
 def call(s,n,a,t):
  with s.ixl: e=s.idx.get(n)
  if e is None: s._rbi()
  with s.ixl: e=s.idx.get(n)
  if e is None: raise RuntimeError(f"unknown tool '{n}'")
  h,rn=e
  return h.cl_t(rn,a,t)
 def rst(s,sid=None):
  ts=[s.cl[sid]] if sid and sid in s.cl else list(s.cl.values())
  for c in ts:
   try: c.rst()
   except: pass
  s._rbi()
 def hlth(s): return [{"id":sid,"alive":c.is_a(),"tools":len(c.tc)} for sid,c in s.cl.items()]
 def any_a(s): return any(c.is_a() for c in s.cl.values())

mgr=MCPM()
ws_clients=set()

def _pt(t):
 with mgr.ixl: e=mgr.idx.get(t)
 if e is None: return None
 h,rn=e
 if not h.cl.acquire(blocking=False): return None
 try:
  if not h.is_a(): return None
  m=h._rq("tools/call",{"name":rn,"arguments":{}},8)
  if not m or m.get("error"): return None
  c=m.get("result",{}).get("content",[])
  return "\n".join(it.get("text","") for it in c if it.get("type")=="text")
 except: return None
 finally: h.cl.release()

def probe():
 t=_pt("list_roblox_studios")
 if t is None: return {"app":None,"place":None}
 try: ss=json.loads(t).get("studios") or []
 except: return {"app":None,"place":None}
 if not ss: return {"app":False,"place":False}
 st=_pt("get_studio_state")
 if st is None: return {"app":True,"place":None}
 low=st.lower(); pl=not any(m in low for m in NO_PLACE)
 return {"app":True,"place":pl}

import re
_LUAU_TIMEOUT=15
def _wl(c):
 h="local _zsS=os.clock();local _zsL="+str(_LUAU_TIMEOUT)+";local function _zsC()if os.clock()-_zsS>_zsL then error('aborted: exceeded '.._zsL..'s limit',2)end end\n"
 c=h+c
 c=re.sub(r'(?m)^(\s*)(while\s+.+?\bdo\b)',r'\1\2 _zsC()',c)
 c=re.sub(r'(?m)^(\s*)(repeat\b)',r'\1\2\n\1_zsC()',c)
 c=re.sub(r'(?m)^(\s*)(for\s+\w+\s*=\s*.*?\bdo\b)',r'\1\2 _zsC()',c)
 return "pcall(function()\n"+c+"\nend)"

# ── DataModel tree summarization ──
# Tools that return potentially massive object trees.
_TREE_TOOLS={"search_game_tree","inspect_instance","explore_subagent"}
# Properties too verbose for LLM context; keep only structural keys.
_KEEP_KEYS={"Name","ClassName","Path","Children","Descendants","InstanceCount","Parent","ChildCount"}
# If JSON text exceeds this char count (~4K tokens), summarize it.
_TREE_CHAR_LIMIT=16000

def _strip_tree(obj):
 """Recursively strip non-structural keys from a parsed JSON tree node."""
 if isinstance(obj,dict):
  out={}
  for k,v in obj.items():
   if k in _KEEP_KEYS: out[k]=_strip_tree(v)
  # Always preserve Name+ClassName at minimum for referential integrity
  if "Name" in obj and "Name" not in out: out["Name"]=obj["Name"]
  if "ClassName" in obj and "ClassName" not in out: out["ClassName"]=obj["ClassName"]
  return out
 if isinstance(obj,list): return [_strip_tree(i) for i in obj]
 return obj

def _summarize(text,tool):
 """If text looks like a DataModel tree and is too large, strip to skeleton."""
 if tool not in _TREE_TOOLS: return text
 if len(text)<=_TREE_CHAR_LIMIT: return text
 try:
  parsed=json.loads(text)
  slim=_strip_tree(parsed)
  out=json.dumps(slim,ensure_ascii=False)
  # If even the skeleton is still massive, collapse children to counts
  if len(out)>_TREE_CHAR_LIMIT*2:
   def _collapse(obj,depth=0):
    if depth>3: return None  # cap depth
    if isinstance(obj,list):
     if len(obj)>20: return f"[{len(obj)} items]"
     return [_collapse(i,depth+1) for i in obj]
    if isinstance(obj,dict):
     r={k:_collapse(v,depth+1) for k,v in obj.items() if k in _KEEP_KEYS}
     if "Name" in obj: r["Name"]=obj["Name"]
     if "ClassName" in obj: r["ClassName"]=obj["ClassName"]
     c=r.get("Children")
     if isinstance(c,list):
      if len(c)>20: r["Children"]=f"[{len(c)} children]"
     return r
    return obj
   trimmed=_collapse(parsed)
   def _count(obj):
    if isinstance(obj,dict): return 1+sum(_count(v) for v in obj.values())
    if isinstance(obj,list): return sum(_count(i) for i in obj)
    return 0
   total=_count(parsed)
   out=json.dumps({"summarized":True,"total_instances":total,"tree":trimmed},ensure_ascii=False)
  return out
 except Exception:
  lines=text.split("\n")
  if len(lines)>120: return "\n".join(lines[:100])+f"\n... [truncated {len(lines)-100} lines]"
  return text[:4000]

def sc(n,a,t):
 if n=="execute_luau" and a.get("code"):
  a=dict(a); a["code"]=_wl(a["code"])
 try:
  r=mgr.call(n,a,t)
  text=_summarize(r["text"],n)
  return {"ok":True,"text":text,"images":r["images"]}
 except TimeoutError as e: return {"ok":False,"error":str(e),"kind":"timeout"}
 except Exception as e: return {"ok":False,"error":str(e),"kind":type(e).__name__}

async def rtt(ws,n,a,t,rid):
 t0=time.monotonic()
 r=await asyncio.to_thread(sc,n,a,t)
 el=time.monotonic()-t0
 tag="92" if r.get("ok") else "91"
 sm=(r.get("text") or r.get("error") or "")[:80].replace("\n"," ")
 sl=" [SLOW]" if el>5 else ""
 _log(f"<- {n} ({el:.1f}s){sl}: {sm}",tag,t=not r.get("ok") or el>5)
 try: await ws.send(json.dumps({"type":"tool_result","id":rid,**r}))
 except websockets.ConnectionClosed: pass

async def hdl(ws):
 peer=getattr(ws,"remote_address",("?",))[0]
 ws_clients.add(ws)
 _log(f"ext connected ({peer}) [{len(ws_clients)} client(s)]","92")
 try:
  _st=await asyncio.to_thread(probe)
  await ws.send(json.dumps({"type":"connected","mcp_alive":mgr.any_a(),"studio":_st["place"],"studio_app":_st["app"],"servers":mgr.hlth(),"tools":mgr.lt(),"port":PORT}))
  async for raw in ws:
   try: m=json.loads(raw)
   except: continue
   mt=m.get("type"); rid=m.get("id")
   if mt=="ping": await ws.send(json.dumps({"type":"pong","id":rid}))
   elif mt=="studio_status":
    st=await asyncio.to_thread(probe)
    await ws.send(json.dumps({"type":"studio_status","id":rid,"studio":st["place"],"studio_app":st["app"],"mcp_alive":mgr.any_a()}))
   elif mt=="list_tools":
    try: tl=await asyncio.to_thread(mgr.lt,True)
    except: tl=mgr.lt()
    _st=await asyncio.to_thread(probe)
    await ws.send(json.dumps({"type":"tools","id":rid,"tools":tl,"mcp_alive":mgr.any_a(),"studio":_st["place"],"studio_app":_st["app"],"servers":mgr.hlth()}))
   elif mt=="call_tool":
    n=m.get("name",""); a=m.get("arguments") or {}; t=float(m.get("timeout",120000))/1000
    _log(f"-> {n}({', '.join(a.keys())})","96",t=False)
    asyncio.create_task(rtt(ws,n,a,t,rid))
   elif mt=="restart_mcp":
    sid=m.get("server")
    try: await asyncio.to_thread(mgr.rst,sid); ok,er=True,None
    except Exception as e: ok,er=False,str(e)
    await ws.send(json.dumps({"type":"mcp_status","id":rid,"alive":mgr.any_a(),"ok":ok,"error":er,"servers":mgr.hlth(),"tools":mgr.lt()}))
   else: await ws.send(json.dumps({"type":"error","id":rid,"error":f"unknown type: {mt}"}))
 except websockets.ConnectionClosed: pass
 except Exception as e: _log(f"handler err: {e}","91")
 finally:
  ws_clients.discard(ws)
  _log(f"ext disconnected [{len(ws_clients)} client(s)]","93")

async def sw():
 backoff={}
 while True:
  await asyncio.sleep(5)
  for sid,c in list(mgr.cl.items()):
   try:
    if not c.is_a():
     b=backoff.get(sid,1)
     if b>60:continue
     _log(f"[{sid}] dead, auto-restart (backoff {b}s)","93"); await asyncio.to_thread(c.start); mgr._rbi()
     if c.is_a():backoff[sid]=1
     else:backoff[sid]=min(b*2,120)
   except Exception as e: _log(f"[{sid}] auto-restart fail: {e}","91")

async def stw(ia,ip=None):
 pa,pa2=ia,ip
 while True:
  await asyncio.sleep(4)
  try: st=await asyncio.to_thread(probe)
  except: continue
  a,p=st["app"],st["place"]
  if a is not None and a!=pa:
   if a: _log(f"Studio connected ({len(mgr.lt())} tools)","92")
   else: _log("Studio disconnected","93")
   pa=a
  if p is not None and p!=pa2:
   await asyncio.sleep(1.2)
   try: cf=(await asyncio.to_thread(probe))["place"]
   except: cf=None
   if cf is None or cf!=p: continue
   if p: _log("Place loaded","92")
   else: _log("Place closed","93")
   pa2=p

async def main():
 print(f"\n  Omni-Ext Bridge - ws://{HOST}:{PORT}\n")
 _log(f"===== START pid={os.getpid()} =====","96")
 ks=await asyncio.to_thread(_check_sp)
 mgr.ld_cfg()
 try: await asyncio.to_thread(mgr.start_all)
 except Exception as e: _log(f"start error: {e}","91")
 tl=len(mgr.lt())
 _st=await asyncio.to_thread(probe)
 if _st["app"] is False:
  for _ in range(8): await asyncio.sleep(1); _st=await asyncio.to_thread(probe); _st.get("app")
 if tl==0 or _st["app"] is False:
  _log("---","93")
  if tl==0: _log("0 tools loaded - Studio not exposing tools yet","93")
  else: _log(f"{tl} tools, no Studio connected","93")
  if ks: _log("Toggle Studio MCP server off/on","93")
  else: _log("Open Studio + enable MCP server","93")
  _log("---","93")
 elif _st["app"]: _log(f"ready ({tl} tools)","92")
 else: _log(f"ready ({tl} tools)","92")
 async with websockets.serve(hdl,HOST,PORT,ping_interval=20,ping_timeout=20,max_size=16777216):
  _log(f"listening on ws://{HOST}:{PORT}","96")
  asyncio.create_task(stw(_st["app"],_st["place"]))
  asyncio.create_task(sw())
  await asyncio.Future()

if __name__=="__main__":
 try: asyncio.run(main())
 except KeyboardInterrupt: _log("shutdown","93")
 finally:
  for c in mgr.cl.values(): c.stp()
  _log("===== STOP =====","96")
