#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct point { int x; int y; };

/* Bug: the loop stops one short, so {2, 4, 6, 8} sums to 12, not 20. */
int sum_range(const int *xs, int n) {
    int total = 0;
    for (int i = 0; i < n - 1; i++)
        total += xs[i];
    return total;
}

double mean(const int *xs, int n) {
    int s = sum_range(xs, n);
    return (double)s / n;
}

int manhattan(struct point a, struct point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

/* Bug: a name that is not in the table leaves hit NULL, and strlen crashes. */
size_t name_len(const char **names, int n, const char *want) {
    const char *hit = NULL;
    for (int i = 0; i < n; i++)
        if (strcmp(names[i], want) == 0) hit = names[i];
    return strlen(hit);
}

int main(int argc, char **argv) {
    /* A signal does not flush a block-buffered stdout. */
    setvbuf(stdout, NULL, _IOLBF, 0);
    int xs[] = {2, 4, 6, 8};
    printf("mean = %.2f (expected 5.00)\n", mean(xs, 4));
    struct point p = {1, 2}, q = {4, 6};
    printf("manhattan = %d\n", manhattan(p, q));
    const char *names[] = {"ada", "brice", "linus"};
    printf("len(brice) = %zu\n", name_len(names, 3, "brice"));
    if (argc > 1)
        printf("len(%s) = %zu\n", argv[1], name_len(names, 3, argv[1]));
    return 0;
}
