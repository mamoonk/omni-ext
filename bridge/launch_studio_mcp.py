"""Launch Roblox Studio's MCP server.

Tries, in order:
1. Built-in MCP via mcp.bat (newer Studio versions, March 2026+)
2. Standalone StudioMCP.exe (older versions / open-source server)
"""

import os, subprocess, sys

MCP_BAT = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Roblox", "mcp.bat")

def _cr():
    r = []
    l = os.environ.get("LOCALAPPDATA")
    if l:
        r.append(os.path.join(l, "Roblox", "Versions"))
    pf = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles")
    if pf:
        r.append(os.path.join(pf, "Roblox", "Versions"))
    return r


def find_mcp_bat():
    if os.path.isfile(MCP_BAT):
        return MCP_BAT
    return None


def find_studio_mcp_exe():
    p, o = [], []
    for root in _cr():
        if not os.path.isdir(root):
            continue
        try:
            for e in os.listdir(root):
                v = os.path.join(root, e)
                ex = os.path.join(v, "StudioMCP.exe")
                if not os.path.isfile(ex):
                    continue
                (p if os.path.isfile(os.path.join(v, "RobloxStudioBeta.exe")) else o).append(ex)
        except OSError:
            continue
    c = p or o
    if not c:
        return None
    c.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return c[0]


def main():
    # Try mcp.bat first (built-in MCP, March 2026+)
    bat = find_mcp_bat()
    if bat:
        sys.stderr.write(f"using {bat}\n")
        sys.stderr.flush()
        p = subprocess.Popen(["cmd.exe", "/c", bat] + sys.argv[1:])
        try:
            return p.wait()
        except KeyboardInterrupt:
            p.terminate()
            return p.wait()

    # Fallback: standalone StudioMCP.exe
    ex = find_studio_mcp_exe()
    if not ex:
        sys.stderr.write(
            "Studio MCP not found.\n"
            "  Open Studio → Assistant → … → Manage MCP Servers → Enable\n"
        )
        return 1
    sys.stderr.write(f"using {ex}\n")
    sys.stderr.flush()
    p = subprocess.Popen([ex] + sys.argv[1:])
    try:
        return p.wait()
    except KeyboardInterrupt:
        p.terminate()
        return p.wait()


if __name__ == "__main__":
    sys.exit(main())
