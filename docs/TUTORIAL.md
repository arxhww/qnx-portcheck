# Codelab: port a Linux C program to QNX 8.0 in 30 minutes with qnx-portcheck

**What you will build:** you take a small Linux echo server that uses `epoll`, `eventfd`, `accept4` and `sched_setaffinity`, find every Linux-only call with a host-side scanner, replace each one with its QNX 8.0 equivalent, and add a CI check that stops new Linux-only calls from coming back.

**What you need:** Python 3.8+ and git. No QNX target, SDP or license is needed for the scan; you need the QNX SDP 8.0 (`qcc`) only for the optional build step at the end.

**Time:** about 30 minutes.

---

## Step 1. Get the tool and the example (2 min)

```sh
git clone https://github.com/arxhww/qnx-portcheck
cd qnx-portcheck
ls examples/linux examples/qnx
```

`examples/linux/echo_server.c` is the program we start from. `examples/qnx/echo_server.c` is the finished port, so you can check your work.

## Step 2. Scan before you touch anything (3 min)

```sh
python3 qnx_portcheck.py examples/linux
```

Output:

```
examples/linux/echo_server.c:9: WARN: sys/epoll.h - Linux-only header
examples/linux/echo_server.c:10: WARN: sys/eventfd.h - Linux-only header
examples/linux/echo_server.c:17: BLOCKER: sched_setaffinity - Not available in QNX 8.0 -> ThreadCtl(_NTO_TCTL_RUNMASK,...) (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/t/threadctl.html)
examples/linux/echo_server.c:19: BLOCKER: eventfd - Not available in QNX 8.0 -> pipe2() or pulses (MsgSendPulse) (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/pipe2.html)
examples/linux/echo_server.c:25: BLOCKER: epoll_create1 - Not available in QNX 8.0 -> poll()/select() or ionotify() (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/poll.html)
examples/linux/echo_server.c:27: BLOCKER: epoll_ctl - Not available in QNX 8.0 -> poll()/select() or ionotify() (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/poll.html)
examples/linux/echo_server.c:29: BLOCKER: epoll_ctl - Not available in QNX 8.0 -> poll()/select() or ionotify() (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/poll.html)
examples/linux/echo_server.c:33: BLOCKER: epoll_wait - Not available in QNX 8.0 -> poll()/select() (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/poll.html)
examples/linux/echo_server.c:36: BLOCKER: accept4 - Not available in QNX 8.0 -> accept() + fcntl(FD_CLOEXEC/O_NONBLOCK) (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/f/fcntl.html)
7 blockers, 2 warnings
```

The exit code is 1 because there are blockers. Read the three levels like this:

- **BLOCKER**: the symbol is a Linux-only API that QNX 8.0 does not provide. The program will not link. Each line gives the replacement and a link to the official QNX 8.0 library reference.
- **WARN**: a Linux-only header or something that behaves differently. Usually it goes away once you fix the blockers that need it.
- **INFO**: supported on QNX but worth a look (for example, behaviour that differs from glibc).

Tip: run it on a real project to size the work before you commit to a port. On iperf3 it reports 7 blockers, and they match the code that the community port in [qnx-ports/iperf3](https://github.com/qnx-ports/iperf3) puts behind `#ifdef`.

## Step 3. Replace the event loop: epoll -> poll (10 min)

QNX has no `epoll`. For a handful of descriptors, `poll()` is the direct replacement and needs the fewest changes. (For many descriptors, or when you want to mix file descriptors with QNX messages, look at `ionotify()` with pulses.)

Before:

```c
int ep = epoll_create1(0);
struct epoll_event ev = { .events = EPOLLIN, .data.fd = srv };
epoll_ctl(ep, EPOLL_CTL_ADD, srv, &ev);
...
int n = epoll_wait(ep, out, 16, -1);
```

After:

```c
#include <poll.h>
struct pollfd fds[2] = { { .fd = srv, .events = POLLIN }, { .fd = stop[0], .events = POLLIN } };
for (;;) {
    if (poll(fds, 2, -1) <= 0) continue;
    if (fds[1].revents & POLLIN) return 0;   /* shutdown */
    if (fds[0].revents & POLLIN) { /* accept a client */ }
}
```

Remove `#include <sys/epoll.h>`; the WARN line disappears with it.

## Step 4. Replace the wake-up channel: eventfd -> pipe (5 min)

`eventfd` is a Linux counter used here only as a "please stop" signal. A plain pipe does the same job and works with `poll()`:

```c
int stop[2];
pipe(stop);                          /* another thread calls write(stop[1], "x", 1) */
fcntl(stop[0], F_SETFL, O_NONBLOCK);
```

If the signal comes from a QNX resource manager or another process, a pulse (`MsgSendPulse`) is the more idiomatic choice. Remove `#include <sys/eventfd.h>`.

## Step 5. Replace accept4 and CPU pinning (5 min)

`accept4(..., SOCK_CLOEXEC)` becomes two calls:

```c
int c = accept(srv, NULL, NULL);
fcntl(c, F_SETFD, FD_CLOEXEC);
```

`sched_setaffinity` becomes a runmask on the calling thread. Bit N means CPU N:

```c
#include <sys/neutrino.h>
ThreadCtl(_NTO_TCTL_RUNMASK, (void *)(uintptr_t)0x1);   /* run on CPU 0 only */
```

Note the difference: on Linux, `sched_setaffinity(0, ...)` sets the affinity of the calling thread, and on QNX the runmask also applies to the calling thread. To pin a whole process, set it in every thread, or use `_NTO_TCTL_RUNMASK_GET_AND_SET_INHERIT` so that new threads inherit it.

## Step 6. Scan again (1 min)

```sh
python3 qnx_portcheck.py examples/qnx
# 0 blockers, 0 warnings   (exit code 0)
```

Compare your file with `examples/qnx/echo_server.c`.

## Step 7. Keep it ported: add the check to CI (4 min)

The scanner writes SARIF, so GitHub shows findings inline on pull requests. Add `.github/workflows/qnx-portcheck.yml`:

```yaml
name: qnx-portcheck
on: [push, pull_request]
permissions:
  contents: read
  security-events: write
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with: { repository: arxhww/qnx-portcheck, path: .portcheck }
      - run: python3 .portcheck/qnx_portcheck.py src --format sarif > portcheck.sarif || true
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: portcheck.sarif }
      - run: python3 .portcheck/qnx_portcheck.py src   # fails the job on blockers
```

Now a pull request that adds `epoll_wait` gets an annotation on the exact line, with the QNX replacement and the doc link.

## Step 8 (optional). Build with the QNX SDP

With QNX SDP 8.0 installed and its environment sourced (`source ~/qnx800/qnxsdp-env.sh`):

```sh
qcc -Vgcc_ntoaarch64le -o echo_server examples/qnx/echo_server.c -lsocket
```

On QNX 8.0 the socket functions live in `libsocket`, which is why `-lsocket` is needed. Copy the binary to the target and test it with `nc <target-ip> 7007`.

## Cheat sheet

| Linux | QNX 8.0 |
|---|---|
| epoll_create/ctl/wait | poll(), select(), or ionotify() + pulses |
| eventfd | pipe()/pipe2() or MsgSendPulse() |
| signalfd | sigwaitinfo() in a dedicated thread |
| timerfd_* | timer_create() with a pulse event |
| accept4 | accept() + fcntl() |
| sched_setaffinity, pthread_setaffinity_np | ThreadCtl(_NTO_TCTL_RUNMASK) |
| sendfile, splice | read()/write() loop |
| prctl(PR_SET_NAME) | pthread_setname_np() |
| statfs/fstatfs | statvfs()/fstatvfs() |
| sysinfo | sysconf() and SYSPAGE_ENTRY() |

The full table, with a doc link for each row, is in `data/equivalents.json`.

## What you learned

- How to measure the Linux-only surface of a codebase before porting.
- The QNX 8.0 replacements for the most common Linux-only calls.
- How to stop regressions with a SARIF check in CI.

qnx-portcheck is an unofficial community tool (MIT), not affiliated with QNX or BlackBerry. Corrections are welcome as issues or pull requests.
