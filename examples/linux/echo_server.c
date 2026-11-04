/* Small Linux-only echo server: epoll loop, eventfd for shutdown, pinned to CPU 0. */
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <netinet/in.h>
#include <sys/epoll.h>
#include <sys/eventfd.h>
#include <sys/socket.h>

int main(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    sched_setaffinity(0, sizeof(set), &set);

    int stop = eventfd(0, EFD_NONBLOCK);
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_port = htons(7007) };
    bind(srv, (struct sockaddr *)&a, sizeof(a));
    listen(srv, 16);

    int ep = epoll_create1(0);
    struct epoll_event ev = { .events = EPOLLIN, .data.fd = srv };
    epoll_ctl(ep, EPOLL_CTL_ADD, srv, &ev);
    ev.data.fd = stop;
    epoll_ctl(ep, EPOLL_CTL_ADD, stop, &ev);

    struct epoll_event out[16];
    for (;;) {
        int n = epoll_wait(ep, out, 16, -1);
        for (int i = 0; i < n; i++) {
            if (out[i].data.fd == stop) return 0;
            int c = accept4(srv, NULL, NULL, SOCK_CLOEXEC);
            char buf[512];
            ssize_t r = read(c, buf, sizeof(buf));
            if (r > 0) write(c, buf, (size_t)r);
            close(c);
        }
    }
}
