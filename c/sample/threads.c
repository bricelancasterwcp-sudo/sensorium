#include <pthread.h>
#include <stdio.h>

/* Each worker calls worker_fn and returns. main joins both, then
   dereferences NULL. Both calls are on the trace before the crash. */
static int worker_fn(int id) {
    return id * 10;
}

static void *worker(void *arg) {
    int id = *(int *)arg;
    int r = worker_fn(id);
    printf("worker %d -> %d\n", id, r);
    fflush(stdout);
    return NULL;
}

int main(void) {
    /* A signal does not flush a block-buffered stdout. */
    setvbuf(stdout, NULL, _IOLBF, 0);
    pthread_t a, b;
    int id0 = 1, id1 = 2;
    pthread_create(&a, NULL, worker, &id0);
    pthread_create(&b, NULL, worker, &id1);
    pthread_join(a, NULL);
    pthread_join(b, NULL);
    int *p = NULL;
    return *p;
}
