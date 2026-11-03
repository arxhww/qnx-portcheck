# qnx-portcheck

Host-side scanner that finds Linux-only APIs in a C/C++ codebase before you port it to QNX 8.0. No QNX hardware or SDK needed: it runs on any machine with Python 3.

It checks source files against the public QNX 8.0 libc reference (1931 symbols) plus a curated table of known Linux-only APIs (epoll, inotify, eventfd, signalfd, timerfd, /proc, backtrace, etc.), and suggests QNX equivalents with doc links.

## Usage

    python3 qnx_portcheck.py path/to/project
    python3 qnx_portcheck.py path/to/file.c --format json
    python3 qnx_portcheck.py path/to/project --format sarif > portcheck.sarif

SARIF output loads in GitHub code scanning and VS Code.

## Findings

Three levels: blockers (Linux-only API with no direct QNX symbol), warnings (differs in behaviour or needs a header/library), info (supported but worth checking).

## Tests

    python3 -m unittest discover tests

Validated on iperf3 (7 consistent blockers).

## License
MIT. Unofficial community tool, not affiliated with QNX or BlackBerry.
