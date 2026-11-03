#include <sys/epoll.h>
#include <stdio.h>
int main(void){ int fd=epoll_create1(0); eventfd(0,0); printf("%d",fd); return 0; }
