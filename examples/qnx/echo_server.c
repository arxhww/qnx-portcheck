/* Same echo server ported to QNX 8.0: poll() loop, self-pipe for shutdown,
 * ThreadCtl(_NTO_TCTL_RUNMASK) for CPU pinning, accept() + fcntl(FD_CLOEXEC). */
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <netinet/in.h>
#include <sys/neutrino.h>
#include <sys/socket.h>

int main(void) {
    ThreadCtl(_NTO_TCTL_RUNMASK, (void *)(uintptr_t)0x1); /* CPU 0 */

    int stop[2];
    pipe(stop);                     /* write(stop[1], "x", 1) to shut down */
    fcntl(stop[0], F_SETFL, O_NONBLOCK);
    int srv = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a = { .sin_family = AF_INET, .sin_port = htons(7007) };
    bind(srv, (struct sockaddr *)&a, sizeof(a));
    listen(srv, 16);

    struct pollfd fds[2] = { { .fd = srv, .events = POLLIN }, { .fd = stop[0], .events = POLLIN } };
    for (;;) {
        if (poll(fds, 2, -1) <= 0) continue;
        if (fds[1].revents & POLLIN) return 0;
        if (fds[0].revents & POLLIN) {
            int c = accept(srv, NULL, NULL);
            fcntl(c, F_SETFD, FD_CLOEXEC);
            char buf[512];
            ssize_t r = read(c, buf, sizeof(buf));
            if (r > 0) write(c, buf, (size_t)r);
            close(c);
        }
    }
}
