#include <setjmp.h>
#include <stdio.h>

/* Unity-shaped runner. test_one fails by longjmp. test_two runs after
   that and returns. The process exits 0. This is the trampoline-repair
   regression: a hijacked return address must not swallow the next test. */
static jmp_buf escape;

static int test_one(void) {
    longjmp(escape, 1);
    return 0;
}

static int test_two(void) {
    return 42;
}

int main(void) {
    if (setjmp(escape) == 0)
        test_one();
    int value = test_two();
    printf("test_two=%d\n", value);
    return 0;
}
