// memstress.c: load the unified memory on purpose, at a chosen duty cycle, for the contention test.
//   memstress <duty_percent> <seconds> [threads] [mb_per_thread]
// Each thread owns two buffers of mb_per_thread MB (default 256 MB, far above the chip's caches) and copies
// one into the other in a loop. Within every 20 ms period it copies for duty_percent of the time and sleeps for
// the rest, so 25 / 50 / 75 approximate a quarter, half and three quarters of the bandwidth one thread set can
// pull; 100 is the maximum. At the end it prints the bytes moved and the achieved GB/s (the real x-axis of the
// contention curve) as "memstress duty=<d> threads=<t> seconds=<s> GB_s=<v>".
// Build: cc -O2 -o memstress memstress.c -lpthread
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int duty = 50, seconds = 60, nthreads = 4;
static size_t mb = 256;
static volatile int stop = 0;

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void* worker(void* arg)
{
    size_t bytes = mb << 20;
    char* a = malloc(bytes);
    char* b = malloc(bytes);
    if (!a || !b) { fprintf(stderr, "memstress: cannot allocate %zu MB\n", 2 * mb); exit(1); }
    memset(a, 1, bytes); memset(b, 2, bytes);
    const double period = 0.020, on = period * duty / 100.0;
    const size_t chunk = 8u << 20;  // 8 MB per copy call, so the duty cycle is kept within ~1 ms
    unsigned long long moved = 0;
    size_t off = 0;
    int flip = 0;
    while (!stop) {
        const double t0 = now_s();
        if (duty > 0) {
            while (!stop && now_s() - t0 < on) {
                if (flip) memcpy(a + off, b + off, chunk); else memcpy(b + off, a + off, chunk);
                moved += chunk;
                off += chunk;
                if (off + chunk > bytes) { off = 0; flip = !flip; }
            }
        }
        if (duty < 100) {
            const double rest = period - (now_s() - t0);
            if (rest > 0) usleep((useconds_t)(rest * 1e6));
        }
    }
    *(unsigned long long*)arg = moved;
    free(a); free(b);
    return NULL;
}

int main(int argc, char** argv)
{
    if (argc < 3) { fprintf(stderr, "usage: memstress <duty_percent> <seconds> [threads] [mb_per_thread]\n"); return 2; }
    duty = atoi(argv[1]); seconds = atoi(argv[2]);
    if (argc > 3) nthreads = atoi(argv[3]);
    if (argc > 4) mb = (size_t)atoi(argv[4]);
    if (duty < 0) duty = 0;
    if (duty > 100) duty = 100;
    pthread_t th[64];
    unsigned long long moved[64] = { 0 };
    if (nthreads > 64) nthreads = 64;
    const double t0 = now_s();
    for (int i = 0; i < nthreads; ++i) pthread_create(&th[i], NULL, worker, &moved[i]);
    while (now_s() - t0 < seconds) usleep(100000);
    stop = 1;
    unsigned long long total = 0;
    for (int i = 0; i < nthreads; ++i) { pthread_join(th[i], NULL); total += moved[i]; }
    const double el = now_s() - t0;
    // every byte is read once and written once: traffic = 2 x bytes copied
    printf("memstress duty=%d threads=%d seconds=%.1f bytes_copied=%llu GB_s=%.2f\n", duty, nthreads, el, total,
           2.0 * total / el / 1e9);
    return 0;
}
