// bwload: a steady memory-bandwidth load from the CPU, for the contention test.
//   bwload <threads> <seconds> <target GB/s, 0 = as fast as possible>
// Every thread copies between two 96 MB buffers (far larger than the caches) in 2 MB chunks and
// sleeps when it is ahead of its share of the target. Bandwidth is counted as read + write
// (a copy of N bytes moves 2N). Prints the achieved bandwidth at the end (also when stopped with kill).
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define BUF (96UL << 20)
#define CHUNK (2UL << 20)

static int threads;
static double secs, target;
static _Atomic unsigned long long total;
static volatile sig_atomic_t stop_now;
static char *volatile sink;  // keeps the compiler from removing the copies (the buffers are never read)
static void on_term(int sig) { (void)sig; stop_now = 1; }

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

static void *work(void *arg) {
    (void)arg;
    char *s = malloc(BUF), *d = malloc(BUF);
    if (!s || !d) return NULL;
    memset(s, 1, BUF);
    memset(d, 0, BUF);
    double rate = target > 0 ? target * 1e9 / threads / 2.0 : 0;  // bytes copied per second per thread
    double t0 = now(), end = t0 + secs;
    unsigned long long done = 0;
    size_t off = 0;
    for (;;) {
        double t = now();
        if (t >= end || stop_now) break;
        if (rate > 0) {
            double ahead = done / rate - (t - t0);
            if (ahead > 0) {
                if (ahead > 0.005) ahead = 0.005;
                struct timespec ts = {0, (long)(ahead * 1e9)};
                nanosleep(&ts, NULL);
                continue;
            }
        }
        memcpy(d + off, s + off, CHUNK);
        sink = d + off;
        __asm__ volatile("" ::: "memory");
        done += CHUNK;
        off += CHUNK;
        if (off >= BUF) off = 0;
    }
    total += done;
    free(s);
    free(d);
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: bwload <threads> <seconds> <target GB/s, 0 = max>\n");
        return 1;
    }
    threads = atoi(argv[1]);
    secs = atof(argv[2]);
    target = atof(argv[3]);
    if (threads < 1) threads = 1;
    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);
    pthread_t *t = calloc(threads, sizeof *t);
    double t0 = now();
    for (int i = 0; i < threads; i++) pthread_create(&t[i], NULL, work, NULL);
    for (int i = 0; i < threads; i++) pthread_join(t[i], NULL);
    double el = now() - t0;
    printf("threads %d seconds %.1f target %.1f GB/s achieved %.1f GB/s\n", threads, el, target,
           2.0 * (double)total / el / 1e9);
    return 0;
}
