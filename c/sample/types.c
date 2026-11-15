#include <stdio.h>

/* No crash. One of each return class v1 decodes, and one of each
   argument class: a const char*, an enum, and a struct by value. */

struct point { int x; int y; };

/* 20 bytes, so the return is memory (SysV), not a register pair. */
struct bigger { int a, b, c, d, e; };

enum color { RED = 1, GREEN = 2, BLUE = 3 };

int ret_int(int n) { return n + 1; }

double ret_double(double x) { return x * 2.0; }

struct point ret_point(int x, int y) {
    struct point p;
    p.x = x;
    p.y = y;
    return p;
}

struct bigger ret_bigger(int n) {
    struct bigger b;
    b.a = n;
    b.b = n + 1;
    b.c = n + 2;
    b.d = n + 3;
    b.e = n + 4;
    return b;
}

int take_all(const char *name, enum color c, struct point p) {
    int n = 0;
    if (name)
        while (name[n]) n++;
    return n + (int)c + p.x + p.y;
}

int main(void) {
    int i = ret_int(41);
    double d = ret_double(1.25);
    struct point p = ret_point(3, 4);
    struct bigger b = ret_bigger(10);
    int t = take_all("brice", GREEN, p);
    printf("int=%d double=%.2f point=%d,%d bigger=%d take=%d\n",
           i, d, p.x, p.y, b.a + b.e, t);
    return 0;
}
