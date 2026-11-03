#include <stdio.h>
#include <poll.h>
int main(void){ struct pollfd p; poll(&p,0,0); puts("ok"); return 0; }
