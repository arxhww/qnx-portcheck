#!/usr/bin/env python3
"""qnx-portcheck: host tool that flags Linux-only APIs when porting C/C++ to QNX 8.0.
Levels: BLOCKER (verified absent), WARN (Linux-only headers), REVIEW (unknown to QNX 8.0 libc index)."""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
EXT = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh"}
WARN_HDR = re.compile(r'^(linux/.*|sys/(epoll|eventfd|signalfd|timerfd|prctl|sysinfo|vfs|sendfile)\.h|execinfo\.h)$')
INC = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]')
CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
KEYWORDS = {"if","for","while","switch","return","sizeof","defined","else","do","catch"}

def load():
    eq = json.load(open(os.path.join(HERE, "data/equivalents.json")))
    ref = json.load(open(os.path.join(HERE, "data/qnx80_libref.json")))
    names = set(ref if isinstance(ref, list) else ref.get("functions", ref.keys()))
    names = {n if isinstance(n, str) else n.get("name") for n in names}
    return eq, names

def strip(src):
    src = re.sub(r'/\*.*?\*/', lambda m: "\n" * m.group().count("\n"), src, flags=re.S)
    return re.sub(r'//[^\n]*', '', src)

def scan_file(path, eq, names, review):
    out = []
    try: text = strip(open(path, errors="replace").read())
    except OSError: return out
    for i, line in enumerate(text.split("\n"), 1):
        m = INC.match(line)
        if m and WARN_HDR.match(m.group(1)):
            out.append(dict(file=path, line=i, level="WARN", symbol=m.group(1), msg="Linux-only header", use=None, doc=None))
            continue
        for c in CALL.finditer(line):
            s = c.group(1)
            if s in KEYWORDS: continue
            if s in eq:
                e = eq[s]
                out.append(dict(file=path, line=i, level="BLOCKER", symbol=s, msg="Not available in QNX 8.0", use=e["use"], doc=e["doc"]))
            elif review and s in names:
                pass
    return out

def main():
    ap = argparse.ArgumentParser(prog="qnx-portcheck")
    ap.add_argument("path"); ap.add_argument("--format", choices=["text","json","sarif"], default="text")
    a = ap.parse_args()
    eq, names = load(); res = []
    if os.path.isfile(a.path): res += scan_file(a.path, eq, names, False)
    for r, _, fs in os.walk(a.path):
        if "/.git" in r: continue
        for f in sorted(fs):
            if os.path.splitext(f)[1] in EXT: res += scan_file(os.path.join(r, f), eq, names, False)
    if a.format == "json": print(json.dumps(res, indent=1))
    elif a.format == "sarif":
        print(json.dumps({"version":"2.1.0","$schema":"https://json.schemastore.org/sarif-2.1.0.json","runs":[{"tool":{"driver":{"name":"qnx-portcheck"}},"results":[
            {"ruleId":x["symbol"],"level":"error" if x["level"]=="BLOCKER" else "warning","message":{"text":x["msg"]+(". Use: "+x["use"] if x["use"] else "")},
             "locations":[{"physicalLocation":{"artifactLocation":{"uri":x["file"]},"region":{"startLine":x["line"]}}}]} for x in res]}]}, indent=1))
    else:
        for x in res:
            print(f'{x["file"]}:{x["line"]}: {x["level"]}: {x["symbol"]} - {x["msg"]}' + (f' -> {x["use"]} ({x["doc"]})' if x["use"] else ""))
        print(f'{sum(x["level"]=="BLOCKER" for x in res)} blockers, {sum(x["level"]=="WARN" for x in res)} warnings')
    sys.exit(1 if any(x["level"]=="BLOCKER" for x in res) else 0)
if __name__ == "__main__": main()
