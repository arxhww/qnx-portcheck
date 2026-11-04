# qnx-portcheck

Host-side scanner that finds Linux-only APIs in a C/C++ codebase before you port it to QNX 8.0. No QNX hardware or SDK needed: it runs on any machine with Python 3.

It checks source files against the public QNX 8.0 libc reference (1931 symbols) plus a curated table of known Linux-only APIs (epoll, inotify, eventfd, signalfd, timerfd, /proc, backtrace, etc.), and suggests QNX equivalents with doc links.

## Tutorial

New to porting? Follow the 30-minute codelab: [docs/TUTORIAL.md](docs/TUTORIAL.md) (Linux echo server with epoll/eventfd -> QNX 8.0, plus a CI check). Before/after code is in `examples/`.

## Usage

    python3 qnx_portcheck.py path/to/project
    python3 qnx_portcheck.py path/to/file.c --format json
    python3 qnx_portcheck.py path/to/project --format sarif > portcheck.sarif

SARIF output loads in GitHub code scanning and VS Code.

As a GitHub Action: `uses: arxhww/qnx-portcheck@main` with `path:` (writes `qnx-portcheck.sarif`). See the tutorial, step 7.

## Findings

Three levels: blockers (Linux-only API with no direct QNX symbol), warnings (differs in behaviour or needs a header/library), info (supported but worth checking).

## Tests

    pip install pytest && pytest tests

Validated on iperf3 (7 consistent blockers).

## License
MIT. Unofficial community tool, not affiliated with QNX or BlackBerry.
