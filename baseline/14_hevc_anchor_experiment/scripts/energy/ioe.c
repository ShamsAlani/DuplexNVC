// ioe.c: energy of every SoC block from the chip's own counters (IOReport "Energy Model" group), no sudo needed.
//   ioe <interval_ms> <samples> <out.csv>
// Writes one row per sample and channel: t_epoch_s, dt_s, channel, unit, energy_mJ (energy used in that interval).
// The channels include the CPU clusters, GPU, ANE (Neural Engine), DRAM and the video encoder/decoder blocks
// (names differ by chip; every channel is logged). Uses the private IOReport library through dlopen.
// Build: cc -O2 -o ioe ioe.c -framework CoreFoundation
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

typedef CFDictionaryRef (*CopyGroup_t)(CFStringRef, CFStringRef, uint64_t, uint64_t, uint64_t);
typedef void* (*CreateSub_t)(void*, CFMutableDictionaryRef, CFMutableDictionaryRef*, uint64_t, CFTypeRef);
typedef CFDictionaryRef (*Samples_t)(void*, CFMutableDictionaryRef, CFTypeRef);
typedef CFDictionaryRef (*Delta_t)(CFDictionaryRef, CFDictionaryRef, CFTypeRef);
typedef CFStringRef (*Str_t)(CFDictionaryRef);
typedef int64_t (*Int_t)(CFDictionaryRef, int32_t);

static double now_s(void) { struct timeval tv; gettimeofday(&tv, NULL); return tv.tv_sec + tv.tv_usec * 1e-6; }

int main(int argc, char** argv)
{
    if (argc < 4) { fprintf(stderr, "usage: ioe <interval_ms> <samples> <out.csv>\n"); return 2; }
    int ms = atoi(argv[1]), n = atoi(argv[2]);
    void* h = dlopen("/usr/lib/libIOReport.dylib", RTLD_NOW);
    if (!h) { fprintf(stderr, "ioe: cannot load libIOReport: %s\n", dlerror()); return 1; }
    CopyGroup_t copyGroup = (CopyGroup_t)dlsym(h, "IOReportCopyChannelsInGroup");
    CreateSub_t createSub = (CreateSub_t)dlsym(h, "IOReportCreateSubscription");
    Samples_t samples = (Samples_t)dlsym(h, "IOReportCreateSamples");
    Delta_t delta = (Delta_t)dlsym(h, "IOReportCreateSamplesDelta");
    Str_t chName = (Str_t)dlsym(h, "IOReportChannelGetChannelName");
    Str_t unitLabel = (Str_t)dlsym(h, "IOReportChannelGetUnitLabel");
    Int_t intValue = (Int_t)dlsym(h, "IOReportSimpleGetIntegerValue");
    if (!copyGroup || !createSub || !samples || !delta || !chName || !unitLabel || !intValue) {
        fprintf(stderr, "ioe: IOReport symbols missing\n"); return 1;
    }
    CFDictionaryRef ch = copyGroup(CFSTR("Energy Model"), NULL, 0, 0, 0);
    if (!ch) { fprintf(stderr, "ioe: no 'Energy Model' channels\n"); return 1; }
    CFMutableDictionaryRef want = CFDictionaryCreateMutableCopy(kCFAllocatorDefault, 0, ch);
    CFMutableDictionaryRef subbed = NULL;
    void* sub = createSub(NULL, want, &subbed, 0, NULL);
    if (!sub) { fprintf(stderr, "ioe: subscription failed\n"); return 1; }
    FILE* f = fopen(argv[3], "w");
    if (!f) { perror("ioe"); return 1; }
    fprintf(f, "t_epoch_s,dt_s,channel,unit,energy_mJ\n");
    CFDictionaryRef prev = samples(sub, subbed, NULL);
    double tp = now_s();
    for (int i = 0; i < n; ++i) {
        usleep(ms * 1000);
        CFDictionaryRef cur = samples(sub, subbed, NULL);
        double tc = now_s();
        CFDictionaryRef d = delta(prev, cur, NULL);
        CFArrayRef arr = (CFArrayRef)CFDictionaryGetValue(d, CFSTR("IOReportChannels"));
        for (CFIndex k = 0; arr && k < CFArrayGetCount(arr); ++k) {
            CFDictionaryRef c = (CFDictionaryRef)CFArrayGetValueAtIndex(arr, k);
            char name[128] = "", unit[16] = "";
            CFStringRef nm = chName(c), un = unitLabel(c);
            if (nm) CFStringGetCString(nm, name, sizeof name, kCFStringEncodingUTF8);
            if (un) CFStringGetCString(un, unit, sizeof unit, kCFStringEncodingUTF8);
            double v = (double)intValue(c, 0);
            double mj = !strcmp(unit, "nJ") ? v / 1e6 : !strcmp(unit, "uJ") ? v / 1e3 : !strcmp(unit, "mJ") ? v : v / 1e6;
            fprintf(f, "%.3f,%.4f,%s,%s,%.6f\n", tc, tc - tp, name, unit, mj);
        }
        CFRelease(d); CFRelease(prev); prev = cur; tp = tc;
        if (i % 50 == 49) fflush(f);
    }
    fclose(f);
    return 0;
}
