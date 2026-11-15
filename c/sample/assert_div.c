#include <assert.h>
#include <stdio.h>

/* assert fires on the second call. The message is part of the expression
   so the trace can show it. The first call returns normally. */
static int checked_div(int a, int b) {
    assert(b != 0 && "divisor must be nonzero");
    return a / b;
}

int main(void) {
    /* abort() does not flush a block-buffered stdout. */
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("ok %d\n", checked_div(10, 2));
    printf("bad %d\n", checked_div(10, 0));
    return 0;
}
