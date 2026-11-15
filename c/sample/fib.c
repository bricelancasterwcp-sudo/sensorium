#include <stdio.h>
#include <stdlib.h>

/* Overhead sample. fib(n) from argv[1], or 27. Time a plain -O0 binary
   against the same source recorded by `sensorium c run`. */
int fib(int n) {
    return n < 2 ? n : fib(n - 1) + fib(n - 2);
}

int main(int argc, char **argv) {
    int n = argc > 1 ? atoi(argv[1]) : 27;
    printf("%d\n", fib(n));
    return 0;
}
