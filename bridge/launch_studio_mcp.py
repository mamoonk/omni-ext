import os, subprocess, sys

def _cr():
 r=[]
 l=os.environ.get("LOCALAPPDATA")
 if l: r.append(os.path.join(l,"Roblox","Versions"))
 pf=os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
 if pf: r.append(os.path.join(pf,"Roblox","Versions"))
 return r

def find():
 p,o=[],[]
 for root in _cr():
  if not os.path.isdir(root): continue
  try:
   for e in os.listdir(root):
    v=os.path.join(root,e); ex=os.path.join(v,"StudioMCP.exe")
    if not os.path.isfile(ex): continue
    (p if os.path.isfile(os.path.join(v,"RobloxStudioBeta.exe")) else o).append(ex)
  except OSError: continue
 c=p or o
 if not c: return None
 c.sort(key=lambda x: os.path.getmtime(x),reverse=True)
 return c[0]

def main():
 ex=find()
 if not ex:
  sys.stderr.write("StudioMCP.exe not found. Open Studio + enable MCP server.\n"); return 1
 sys.stderr.write(f"using {ex}\n"); sys.stderr.flush()
 p=subprocess.Popen([ex]+sys.argv[1:])
 try: return p.wait()
 except KeyboardInterrupt: p.terminate(); return p.wait()

if __name__=="__main__": sys.exit(main())
