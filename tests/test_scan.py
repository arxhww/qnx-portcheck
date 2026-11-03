import json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).parent
SCRIPT = ROOT.parent / "qnx_portcheck.py"
def run(f, fmt="json"):
    return subprocess.run([sys.executable, str(SCRIPT), "--format", fmt, str(ROOT/"fixtures"/f)], capture_output=True, text=True)
def test_linux_blocks():
    r = run("linuxy.c")
    assert r.returncode != 0
    assert "epoll" in r.stdout
def test_clean_passes():
    assert run("clean.c").returncode == 0
def test_sarif_valid():
    assert json.loads(run("linuxy.c", "sarif").stdout)["version"] == "2.1.0"
