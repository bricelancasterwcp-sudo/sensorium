/* Linux x86-64 recorder runtime. Wire format: sensorium.c.format (v1).
 * Linked into programs built with -g -fno-omit-frame-pointer -fno-inline
 * -finstrument-functions. Inactive unless SENSORIUM_C_ROOT is set.
 *
 * cfa = callee rbp + 16. At -O0, DW_OP_fbreg is relative to that CFA.
 * glibc 2.41 mangles jmp_buf rbp/rsp/pc as ROL(value ^ %fs:0x30, 17).
 */
#define _GNU_SOURCE
/* Ubuntu's gcc defines _FORTIFY_SOURCE when optimizing. glibc then
 * renames longjmp, _longjmp, and siglongjmp onto __longjmp_chk (an asm
 * label, or a macro when the compiler has no asm labels). The four
 * interposers below have to stay four symbols: fortified callers enter
 * at __longjmp_chk, everyone else at longjmp. This file does not need
 * fortify of its own, and the level is latched by the first include. */
#undef _FORTIFY_SOURCE

#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <link.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ucontext.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <unistd.h>

#define NOI __attribute__((no_instrument_function))

#define NO_SLOT ((int32_t)(-2147483647 - 1))
#define FLAG_CSTR 1
#define FLAG_TRUNC 2
#define RET_MEM 3
#define STR_CAP 64
#define PARAM_CAP 256
#define STACK_BYTES 512
#define ASSERT_CLIP 200
#define SHADOW_MAX 4096
#define MAX_THREADS 256
#define MAX_OBJS 128
#define MAX_LOADS 8
#define MAX_FUNCS 16384
#define MAX_PARAMS 65536
#define BUF_SIZE (1 << 16)
#define BLOB_MAX (1 << 14)
#define ARCH_SHSTK_STATUS_ 0x5005
#define PAGE 4096u

struct param_plan {
    int32_t off;
    uint16_t size;
    uint16_t flags;
};

struct func_plan {
    uint64_t addr; /* unrelocated low_pc */
    uint32_t param_index;
    uint16_t nparams;
    uint16_t ret_size;
    uint8_t ret_class;
    uint8_t ret_nreg;
};

struct load_range {
    uint64_t lo, hi;
};

struct obj_mod {
    uint64_t bias;
    struct load_range loads[MAX_LOADS];
    int nloads;
    uint32_t func_begin;
    uint32_t nfuncs;
};

struct shadow_ent {
    uint64_t *slot;
    uint64_t orig;
    uint64_t rbp;
    uint16_t ret_size;
    uint8_t ret_class;
};

struct tstate {
    uint32_t tid;
    int fd;
    atomic_int dead;
    atomic_size_t pub_len;  /* bytes of buf[] visible to a crash */
    atomic_size_t disk_len; /* prefix of buf[] already write()'d */
    size_t len;             /* owner-only logical length */
    int depth;
    unsigned char buf[BUF_SIZE];
    unsigned char scratch[BLOB_MAX];
    struct shadow_ent shadow[SHADOW_MAX];
};

struct hit {
    int found;
    uint8_t ret_class;
    uint16_t ret_size;
    uint16_t nparams;
    uint32_t param_index;
};

typedef void (*lj_fn)(struct __jmp_buf_tag *, int);
typedef void (*assert_fn)(const char *, const char *, unsigned, const char *);
typedef pid_t (*fork_fn)(void);
typedef int (*thr_fn)(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);

extern void sensorium_ret_tramp(void);

static struct param_plan g_params[MAX_PARAMS];
static struct func_plan g_funcs[MAX_FUNCS];
static struct obj_mod g_objs[MAX_OBJS];
static unsigned g_nparams;
static unsigned g_nfuncs;
static atomic_int g_nobjs;
static atomic_int g_scan_lock;
static __thread int g_scanning;

static atomic_int g_on;
static atomic_int g_cet;
static int g_no_retval;
static atomic_int g_crashing;
static atomic_uint_fast64_t g_seq = 1;
static atomic_uint g_next_tid = 1;
static atomic_uint g_started;
static atomic_int g_resolved;
static pid_t g_proc_pid;
static char g_root[4096];
static char g_proc[4096];
static char g_exe[4096];
static char g_objs_txt[65536];
static size_t g_objs_len;
static char *g_argv_json;
static size_t g_argv_len;
static pid_t g_kids[256];
static int g_nkids;

static _Atomic uintptr_t g_reg[MAX_THREADS];
static atomic_uint g_nreg;

static __thread struct tstate *ts_;
static pthread_key_t g_key;
static int g_key_ok;

static lj_fn real_longjmp, real__longjmp, real_siglongjmp, real___longjmp_chk;
static assert_fn real_assert_fail;
static fork_fn real_fork;
static thr_fn real_pthread_create;

NOI static void resolve_syms(void);
NOI static void flush_claim(struct tstate *t);
NOI static void emit(struct tstate *t, uint8_t kind, uint64_t a, uint64_t b,
                     uint64_t c, uint64_t d, const void *extra, uint32_t elen);
NOI static struct tstate *me(void);
NOI static void child_switch(void);
NOI static void write_threads_json(void);
NOI static void repair_longjmp(struct __jmp_buf_tag *env);

NOI static void pause_once(void) {
    __asm__ volatile("pause");
}

NOI static int write_full(int fd, const void *buf, size_t n) {
    const unsigned char *p = buf;
    size_t off = 0;
    while (off < n) {
        ssize_t w = write(fd, p + off, n - off);
        if (w < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        if (w == 0) return -1;
        off += (size_t)w;
    }
    return 0;
}

NOI static char *ap_str(char *p, char *end, const char *s) {
    while (*s && p < end) *p++ = *s++;
    return p;
}

NOI static char *ap_u(char *p, char *end, unsigned long v) {
    char rev[32];
    int r = 0;
    if (v == 0) rev[r++] = '0';
    while (v) {
        rev[r++] = (char)('0' + (v % 10));
        v /= 10;
    }
    while (r && p < end) *p++ = rev[--r];
    return p;
}

NOI static int join2(char *dst, size_t cap, const char *a, const char *b) {
    size_t na = strlen(a), nb = strlen(b);
    if (na + 1 + nb + 1 > cap) {
        if (cap) dst[0] = 0;
        return -1;
    }
    memcpy(dst, a, na);
    dst[na] = '/';
    memcpy(dst + na + 1, b, nb + 1);
    return 0;
}

NOI static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

NOI static size_t copy_mem(void *dst, uintptr_t src, size_t n) {
    size_t got = 0;
    unsigned char *d = dst;
    if (n == 0 || src == 0) return 0;
    while (got < n) {
        size_t left = PAGE - (size_t)(src & (PAGE - 1));
        size_t chunk = n - got;
        struct iovec li, ri;
        ssize_t r;
        if (chunk > left) chunk = left;
        li.iov_base = d + got;
        li.iov_len = chunk;
        ri.iov_base = (void *)src;
        ri.iov_len = chunk;
        do {
            r = process_vm_readv(getpid(), &li, 1, &ri, 1, 0);
        } while (r < 0 && errno == EINTR);
        if (r < 0) break;
        got += (size_t)r;
        src += (uintptr_t)r;
        if ((size_t)r != chunk) break;
    }
    return got;
}

/* ---- thread buffer -------------------------------------------------- */

NOI static void flush_claim(struct tstate *t) {
    size_t disk, pub;
    if (!t || t->fd < 0) return;
    disk = atomic_load_explicit(&t->disk_len, memory_order_relaxed);
    pub = atomic_load_explicit(&t->pub_len, memory_order_acquire);
    if (pub <= disk) return;
    if (!atomic_compare_exchange_strong_explicit(
            &t->disk_len, &disk, pub,
            memory_order_acq_rel, memory_order_relaxed))
        return;
    (void)write_full(t->fd, t->buf + disk, pub - disk);
}

NOI static void emit(struct tstate *t, uint8_t kind, uint64_t a, uint64_t b,
                     uint64_t c, uint64_t d, const void *extra, uint32_t elen) {
    unsigned char *p;
    uint64_t seq, ts;
    uint32_t total;
    if (!t || t->fd < 0) return;
    if (elen > BUF_SIZE - 56) elen = BUF_SIZE - 56;
    total = 56u + elen;
    if (t->len + total > BUF_SIZE) {
        flush_claim(t);
        if (!atomic_load_explicit(&g_crashing, memory_order_relaxed) &&
            atomic_load_explicit(&t->disk_len, memory_order_relaxed) == t->len &&
            atomic_load_explicit(&t->pub_len, memory_order_relaxed) == t->len) {
            t->len = 0;
            atomic_store_explicit(&t->pub_len, 0, memory_order_relaxed);
            atomic_store_explicit(&t->disk_len, 0, memory_order_relaxed);
        }
    }
    if (t->len + total > BUF_SIZE) return;
    p = t->buf + t->len;
    memset(p, 0, 56);
    p[0] = kind;
    seq = atomic_fetch_add_explicit(&g_seq, 1, memory_order_relaxed);
    ts = now_ns();
    memcpy(p + 4, &seq, 8);
    memcpy(p + 12, &ts, 8);
    memcpy(p + 20, &a, 8);
    memcpy(p + 28, &b, 8);
    memcpy(p + 36, &c, 8);
    memcpy(p + 44, &d, 8);
    memcpy(p + 52, &elen, 4);
    if (elen && extra) memcpy(p + 56, extra, elen);
    t->len += total;
    /* Publish only after the bytes are in place. A crash mid-record
     * keeps the previous length, so at most this record is lost. */
    atomic_store_explicit(&t->pub_len, t->len, memory_order_release);
}

/* ---- plans ---------------------------------------------------------- */

NOI static int obj_contains(const struct obj_mod *o, uint64_t fn) {
    int i;
    for (i = 0; i < o->nloads; i++) {
        if (fn >= o->loads[i].lo && fn < o->loads[i].hi) return 1;
    }
    return 0;
}

NOI static int find_hit(uint64_t fn, struct hit *h) {
    int n, i;
    memset(h, 0, sizeof *h);
    n = atomic_load_explicit(&g_nobjs, memory_order_acquire);
    for (i = 0; i < n; i++) {
        const struct obj_mod *o = &g_objs[i];
        uint64_t rel;
        uint32_t lo, hi;
        if (!obj_contains(o, fn)) continue;
        rel = fn - o->bias;
        lo = 0;
        hi = o->nfuncs;
        while (lo < hi) {
            uint32_t mid = lo + (hi - lo) / 2;
            uint64_t a = g_funcs[o->func_begin + mid].addr;
            if (a == rel) {
                const struct func_plan *fp = &g_funcs[o->func_begin + mid];
                h->found = 1;
                h->ret_class = fp->ret_class;
                h->ret_size = fp->ret_size;
                h->nparams = fp->nparams;
                h->param_index = fp->param_index;
                return 1;
            }
            if (a < rel) lo = mid + 1;
            else hi = mid;
        }
        return 0; /* in this image, but not in its plan */
    }
    return 0;
}

NOI static int cmp_func(const void *a, const void *b) {
    const struct func_plan *fa = a, *fb = b;
    if (fa->addr < fb->addr) return -1;
    if (fa->addr > fb->addr) return 1;
    return 0;
}

NOI static void load_plan_file(const char *path, struct obj_mod *o) {
    int fd;
    struct stat st;
    unsigned char *buf = NULL;
    size_t nread = 0;
    uint32_t ver = 0, count = 0;
    size_t pos, i;
    uint32_t begin;
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) return;
    if (fstat(fd, &st) < 0 || st.st_size < 12 || st.st_size > 64 * 1024 * 1024) {
        close(fd);
        return;
    }
    buf = malloc((size_t)st.st_size);
    if (!buf) {
        close(fd);
        return;
    }
    while (nread < (size_t)st.st_size) {
        ssize_t r = read(fd, buf + nread, (size_t)st.st_size - nread);
        if (r < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (r == 0) break;
        nread += (size_t)r;
    }
    close(fd);
    if (nread != (size_t)st.st_size || memcmp(buf, "SCPL", 4) != 0) {
        free(buf);
        return;
    }
    memcpy(&ver, buf + 4, 4);
    memcpy(&count, buf + 8, 4);
    if (ver != 1) {
        free(buf);
        return;
    }
    begin = g_nfuncs;
    pos = 12;
    for (i = 0; i < count; i++) {
        struct func_plan fp;
        uint16_t np, p;
        if (pos + 14 > nread) break;
        if (g_nfuncs >= MAX_FUNCS) break;
        memset(&fp, 0, sizeof fp);
        memcpy(&fp.addr, buf + pos, 8);
        fp.ret_class = buf[pos + 8];
        fp.ret_nreg = buf[pos + 9];
        memcpy(&fp.ret_size, buf + pos + 10, 2);
        memcpy(&np, buf + pos + 12, 2);
        pos += 14;
        fp.param_index = g_nparams;
        fp.nparams = 0;
        for (p = 0; p < np; p++) {
            struct param_plan pp;
            if (pos + 8 > nread) {
                pos = nread + 1;
                break;
            }
            if (g_nparams >= MAX_PARAMS) {
                pos += 8;
                continue;
            }
            memcpy(&pp.off, buf + pos, 4);
            memcpy(&pp.size, buf + pos + 4, 2);
            memcpy(&pp.flags, buf + pos + 6, 2);
            pos += 8;
            g_params[g_nparams++] = pp;
            fp.nparams++;
        }
        if (pos > nread) break;
        g_funcs[g_nfuncs++] = fp;
    }
    o->func_begin = begin;
    o->nfuncs = g_nfuncs - begin;
    if (o->nfuncs > 1)
        qsort(g_funcs + begin, o->nfuncs, sizeof(struct func_plan), cmp_func);
    free(buf);
}

NOI static int known_bias(uint64_t bias) {
    int n = atomic_load_explicit(&g_nobjs, memory_order_relaxed);
    int i;
    for (i = 0; i < n; i++)
        if (g_objs[i].bias == bias) return 1;
    return 0;
}

NOI static void objs_add(uint64_t bias, const char *name) {
    char line[4200];
    int n;
    size_t len;
    n = snprintf(line, sizeof line, "%lx %s\n", (unsigned long)bias, name);
    if (n < 0) return;
    len = (size_t)n;
    if (len >= sizeof line) return;
    if (g_objs_len + len >= sizeof g_objs_txt) return;
    memcpy(g_objs_txt + g_objs_len, line, len);
    g_objs_len += len;
}

NOI static void write_objs_file(void) {
    char path[4200];
    int fd;
    if (join2(path, sizeof path, g_proc, "objs.txt") != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, g_objs_txt, g_objs_len);
    close(fd);
}

NOI static int phdr_cb(struct dl_phdr_info *info, size_t sz, void *data) {
    struct obj_mod o;
    const char *name;
    int j, slot;
    char *plan = NULL;
    (void)sz;
    (void)data;
    name = (info->dlpi_name && info->dlpi_name[0]) ? info->dlpi_name : "<exe>";
    objs_add((uint64_t)info->dlpi_addr, name);
    if (known_bias((uint64_t)info->dlpi_addr)) return 0;
    slot = atomic_load_explicit(&g_nobjs, memory_order_relaxed);
    if (slot >= MAX_OBJS) return 0;
    memset(&o, 0, sizeof o);
    o.bias = (uint64_t)info->dlpi_addr;
    for (j = 0; j < (int)info->dlpi_phnum && o.nloads < MAX_LOADS; j++) {
        const ElfW(Phdr) *ph = &info->dlpi_phdr[j];
        if (ph->p_type != PT_LOAD || ph->p_memsz == 0) continue;
        o.loads[o.nloads].lo = o.bias + (uint64_t)ph->p_vaddr;
        o.loads[o.nloads].hi = o.loads[o.nloads].lo + (uint64_t)ph->p_memsz;
        o.nloads++;
    }
    if (name[0] == '<' ) {
        size_t el = strlen(g_exe);
        plan = malloc(el + 8);
        if (plan) {
            memcpy(plan, g_exe, el);
            memcpy(plan + el, ".scplan", 8);
        }
    } else {
        size_t el = strlen(info->dlpi_name);
        plan = malloc(el + 8);
        if (plan) {
            memcpy(plan, info->dlpi_name, el);
            memcpy(plan + el, ".scplan", 8);
        }
    }
    if (plan) {
        load_plan_file(plan, &o);
        free(plan);
    }
    g_objs[slot] = o;
    atomic_store_explicit(&g_nobjs, slot + 1, memory_order_release);
    return 0;
}

NOI static void scan_phdrs(void) {
    int exp;
    if (g_scanning) return;
    g_scanning = 1;
    exp = 0;
    while (!atomic_compare_exchange_weak_explicit(
        &g_scan_lock, &exp, 1, memory_order_acquire, memory_order_relaxed)) {
        exp = 0;
        pause_once();
    }
    g_objs_len = 0;
    dl_iterate_phdr(phdr_cb, NULL);
    write_objs_file();
    atomic_store_explicit(&g_scan_lock, 0, memory_order_release);
    g_scanning = 0;
}

/* ---- argument blob -------------------------------------------------- */

NOI static int read_cstr(uintptr_t ptr, unsigned char *dst, int *slen) {
    unsigned char tmp[STR_CAP];
    size_t got, i;
    if (ptr == 0) {
        *slen = -2;
        return 0;
    }
    got = copy_mem(tmp, ptr, STR_CAP);
    if (got == 0) {
        *slen = -1;
        return 0;
    }
    for (i = 0; i < got; i++) {
        if (tmp[i] == 0) {
            *slen = (int)i;
            if (i) memcpy(dst, tmp, i);
            return 0;
        }
    }
    *slen = (int)got;
    memcpy(dst, tmp, got);
    return 0;
}

NOI static uint32_t build_blob(const struct hit *h, int have_fp, uint64_t cfa,
                              unsigned char *dst, size_t cap) {
    unsigned char *p = dst;
    unsigned char *end = dst + cap;
    uint16_t n = 0, i;
    uint16_t zero = 0;
    if (!h->found || !have_fp) {
        if (cap < 4) return 0;
        memcpy(dst, &zero, 2);
        memcpy(dst + 2, &zero, 2);
        return 4;
    }
    if (cap < 4) return 0;
    p += 4; /* patch nparams at the end */
    for (i = 0; i < h->nparams; i++) {
        const struct param_plan *pp = &g_params[h->param_index + i];
        uint16_t flags = pp->flags;
        uint16_t copy = pp->size;
        unsigned char raw[PARAM_CAP];
        unsigned char sbuf[STR_CAP];
        int slen = -1;
        int want_str = (flags & FLAG_CSTR) != 0;
        size_t need;
        if (pp->off == NO_SLOT || pp->size == 0) copy = 0;
        else if (copy > PARAM_CAP) {
            copy = PARAM_CAP;
            flags = (uint16_t)(flags | FLAG_TRUNC);
        }
        if (copy) {
            uint64_t addr = cfa + (int64_t)pp->off;
            size_t got = copy_mem(raw, (uintptr_t)addr, copy);
            /* A bad slot is a missing argument, not a crash in the hook. */
            if (got != copy) {
                copy = 0;
                flags = (uint16_t)(flags & (uint16_t)~(FLAG_CSTR | FLAG_TRUNC));
                want_str = 0;
            }
        }
        if (want_str) {
            if (pp->off == NO_SLOT || pp->size < 8 || !copy) slen = -1;
            else {
                uint64_t ptr = 0;
                memcpy(&ptr, raw, 8);
                read_cstr((uintptr_t)ptr, sbuf, &slen);
            }
        }
        need = 8u + copy;
        if (want_str) {
            need += 4;
            if (slen > 0) need += (size_t)slen;
        }
        if (p + need > end) break;
        memcpy(p, &pp->off, 4);
        p += 4;
        memcpy(p, &copy, 2);
        p += 2;
        memcpy(p, &flags, 2);
        p += 2;
        if (copy) {
            memcpy(p, raw, copy);
            p += copy;
        }
        if (want_str) {
            int32_t sl = slen;
            memcpy(p, &sl, 4);
            p += 4;
            if (slen > 0) {
                memcpy(p, sbuf, (size_t)slen);
                p += slen;
            }
        }
        n++;
    }
    memcpy(dst, &n, 2);
    memcpy(dst + 2, &zero, 2);
    return (uint32_t)(p - dst);
}

/* ---- meta files ----------------------------------------------------- */

NOI static int mkdir_0700(const char *path) {
    if (mkdir(path, 0700) == 0 || errno == EEXIST) {
        (void)chmod(path, 0700);
        return 0;
    }
    return -1;
}

NOI static int ensure_dirs(pid_t pid) {
    char tmp[32];
    int tn = 0;
    unsigned long v;
    size_t rl;
    g_proc_pid = pid;
    if (mkdir(g_root, 0700) == 0) (void)chmod(g_root, 0700);
    v = (unsigned long)pid;
    if (v == 0) tmp[tn++] = '0';
    else {
        char rev[32];
        int r = 0;
        while (v) {
            rev[r++] = (char)('0' + (v % 10));
            v /= 10;
        }
        while (r) tmp[tn++] = rev[--r];
    }
    tmp[tn] = 0;
    rl = strlen(g_root);
    if (rl + 1 + (size_t)tn + 1 > sizeof g_proc) return -1;
    memcpy(g_proc, g_root, rl);
    g_proc[rl] = '/';
    memcpy(g_proc + rl + 1, tmp, (size_t)tn + 1);
    if (mkdir_0700(g_proc) != 0) return -1;
    {
        char th[4200];
        if (join2(th, sizeof th, g_proc, "threads") != 0) return -1;
        if (mkdir_0700(th) != 0) return -1;
    }
    return 0;
}

NOI static void write_boot(void) {
    char path[4200];
    char body[8192];
    char *p, *end;
    struct timespec ts;
    int fd;
    const char *s;
    if (join2(path, sizeof path, g_proc, "boot.json") != 0) return;
    clock_gettime(CLOCK_REALTIME, &ts);
    p = body;
    end = body + sizeof body - 4;
    p = ap_str(p, end, "{\"start_ts\":");
    p = ap_u(p, end, (unsigned long)ts.tv_sec);
    if (p < end) *p++ = '.';
    {
        unsigned long nsec = (unsigned long)ts.tv_nsec;
        char rev[9];
        int i;
        for (i = 0; i < 9; i++) {
            rev[i] = (char)('0' + (nsec % 10));
            nsec /= 10;
        }
        for (i = 8; i >= 0 && p < end; i--) *p++ = rev[i];
    }
    p = ap_str(p, end, ",\"exe\":\"");
    for (s = g_exe; *s && p + 2 < end; s++) {
        if (*s == '"' || *s == '\\') *p++ = '\\';
        *p++ = *s;
    }
    p = ap_str(p, end, "\"}\n");
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, body, (size_t)(p - body));
    close(fd);
}

NOI static void json_escape_write(int fd, const char *s, size_t n) {
    size_t i;
    (void)write_full(fd, "\"", 1);
    for (i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        char buf[8];
        if (c == '"' || c == '\\') {
            buf[0] = '\\';
            buf[1] = (char)c;
            (void)write_full(fd, buf, 2);
        } else if (c == '\n') {
            (void)write_full(fd, "\\n", 2);
        } else if (c == '\r') {
            (void)write_full(fd, "\\r", 2);
        } else if (c == '\t') {
            (void)write_full(fd, "\\t", 2);
        } else if (c < 0x20) {
            static const char hex[] = "0123456789abcdef";
            buf[0] = '\\';
            buf[1] = 'u';
            buf[2] = '0';
            buf[3] = '0';
            buf[4] = hex[c >> 4];
            buf[5] = hex[c & 0xf];
            (void)write_full(fd, buf, 6);
        } else {
            (void)write_full(fd, &c, 1);
        }
    }
    (void)write_full(fd, "\"", 1);
}

NOI static void write_argv(void) {
    char path[4200];
    char *raw;
    int inf, out;
    ssize_t n;
    size_t i, start;
    int first = 1;
    raw = malloc(1 << 16);
    if (!raw) return;
    inf = open("/proc/self/cmdline", O_RDONLY | O_CLOEXEC);
    if (inf < 0) {
        free(raw);
        return;
    }
    n = read(inf, raw, (1 << 16) - 1);
    close(inf);
    if (n < 0) n = 0;
    raw[n] = 0;
    if (join2(path, sizeof path, g_proc, "argv.json") != 0) {
        free(raw);
        return;
    }
    out = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (out < 0) {
        free(raw);
        return;
    }
    (void)write_full(out, "[", 1);
    start = 0;
    for (i = 0; i <= (size_t)n; i++) {
        if (i == (size_t)n || raw[i] == 0) {
            /* i == start is an empty argument (two NULs) or the end. */
            if (i == start && i == (size_t)n) break;
            if (i == start && !(i < (size_t)n)) break;
            if (!first) (void)write_full(out, ",", 1);
            first = 0;
            json_escape_write(out, raw + start, i - start);
            if (i == (size_t)n) break;
            start = i + 1;
            if (start >= (size_t)n) break;
        }
    }
    (void)write_full(out, "]\n", 2);
    close(out);
    /* Replay buffer so a forked child can rewrite argv.json with write()
     * only, without taking the malloc lock. */
    free(raw);
    /* Read the file we just wrote into the child-replay buffer. */
    {
        int fd = open(path, O_RDONLY | O_CLOEXEC);
        struct stat st;
        if (fd >= 0 && fstat(fd, &st) == 0 && st.st_size > 0 &&
            st.st_size < (1 << 20)) {
            char *copy = malloc((size_t)st.st_size);
            if (copy) {
                size_t got = 0;
                while (got < (size_t)st.st_size) {
                    ssize_t r = read(fd, copy + got, (size_t)st.st_size - got);
                    if (r < 0) {
                        if (errno == EINTR) continue;
                        break;
                    }
                    if (r == 0) break;
                    got += (size_t)r;
                }
                if (got == (size_t)st.st_size) {
                    free(g_argv_json);
                    g_argv_json = copy;
                    g_argv_len = got;
                } else {
                    free(copy);
                }
            }
        }
        if (fd >= 0) close(fd);
    }
}

NOI static void write_warn_cet(void) {
    char path[4200];
    int fd;
    static const char msg[] =
        "cet: shadow stack enabled; return values not recorded\n";
    if (join2(path, sizeof path, g_proc, "warn.txt") != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, msg, sizeof msg - 1);
    close(fd);
}

NOI static void cet_check(void) {
    unsigned long status = 0;
    long rc = syscall(SYS_arch_prctl, ARCH_SHSTK_STATUS_, &status);
    /* EINVAL means the kernel has no shadow-stack prctl. CET is off. */
    if (rc == 0 && (status & 1ul)) {
        atomic_store_explicit(&g_cet, 1, memory_order_relaxed);
        write_warn_cet();
    }
}

NOI static void write_exit_status(int code) {
    char path[4200];
    char body[64];
    char *p, *end;
    int fd;
    if (join2(path, sizeof path, g_proc, "exit.json") != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) return;
    p = body;
    end = body + sizeof body;
    p = ap_str(p, end, "{\"status\": ");
    if (code < 0) {
        if (p < end) *p++ = '-';
        p = ap_u(p, end, (unsigned long)(-(long)code));
    } else {
        p = ap_u(p, end, (unsigned long)code);
    }
    p = ap_str(p, end, "}\n");
    (void)write_full(fd, body, (size_t)(p - body));
    close(fd);
}

NOI static void write_exit_signal(int sig) {
    char path[4200];
    char body[64];
    char *p, *end;
    int fd;
    if (join2(path, sizeof path, g_proc, "exit.json") != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) return;
    p = body;
    end = body + sizeof body;
    p = ap_str(p, end, "{\"signal\": ");
    p = ap_u(p, end, (unsigned long)sig);
    p = ap_str(p, end, "}\n");
    (void)write_full(fd, body, (size_t)(p - body));
    close(fd);
}

NOI static void write_threads_json(void) {
    char path[4200];
    char body[8192];
    char *p, *end;
    unsigned n, i;
    int first = 1;
    int fd;
    if (join2(path, sizeof path, g_proc, "threads.json") != 0) return;
    p = body;
    end = body + sizeof body - 8;
    p = ap_str(p, end, "{\"started\": ");
    p = ap_u(p, end, (unsigned long)atomic_load_explicit(&g_started, memory_order_relaxed));
    p = ap_str(p, end, ", \"live\": [");
    n = atomic_load_explicit(&g_nreg, memory_order_acquire);
    if (n > MAX_THREADS) n = MAX_THREADS;
    for (i = 0; i < n; i++) {
        uintptr_t bits = atomic_load_explicit(&g_reg[i], memory_order_acquire);
        struct tstate *t;
        if (!bits) continue;
        t = (struct tstate *)bits;
        if (atomic_load_explicit(&t->dead, memory_order_acquire)) continue;
        if (!first) p = ap_str(p, end, ", ");
        if (p >= end - 16) break;
        first = 0;
        p = ap_u(p, end, t->tid);
    }
    p = ap_str(p, end, "]}\n");
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, body, (size_t)(p - body));
    close(fd);
}

NOI static void write_forks_json(void) {
    char path[4200];
    char body[4096];
    char *p, *end;
    int i, fd;
    if (join2(path, sizeof path, g_proc, "forks.json") != 0) return;
    p = body;
    end = body + sizeof body - 4;
    p = ap_str(p, end, "[");
    for (i = 0; i < g_nkids; i++) {
        if (i) p = ap_str(p, end, ", ");
        if (p >= end - 24) break;
        p = ap_u(p, end, (unsigned long)g_kids[i]);
    }
    p = ap_str(p, end, "]\n");
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, body, (size_t)(p - body));
    close(fd);
}

/* ---- threads -------------------------------------------------------- */

NOI static void open_thread_file(struct tstate *t) {
    char path[4200];
    char tail[64];
    char *q, *end;
    unsigned char hdr[8];
    int fd;
    q = tail;
    end = tail + sizeof tail;
    q = ap_str(q, end, "threads/t");
    q = ap_u(q, end, t->tid);
    q = ap_str(q, end, ".bin");
    if (q >= end) return;
    *q = 0;
    if (join2(path, sizeof path, g_proc, tail) != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    memcpy(hdr, "SCR1", 4);
    memcpy(hdr + 4, &t->tid, 4);
    if (write_full(fd, hdr, 8) != 0) {
        close(fd);
        return;
    }
    t->fd = fd;
}

NOI static void thread_dead(void *p) {
    struct tstate *t = p;
    if (!t) return;
    flush_claim(t);
    atomic_store_explicit(&t->dead, 1, memory_order_release);
}

NOI static struct tstate *me(void) {
    struct tstate *t;
    unsigned slot;
    uint32_t tid;
    if (ts_) return ts_;
    t = calloc(1, sizeof *t);
    if (!t) return NULL;
    tid = atomic_fetch_add_explicit(&g_next_tid, 1, memory_order_relaxed);
    t->tid = tid;
    t->fd = -1;
    if (tid != 1)
        atomic_fetch_add_explicit(&g_started, 1, memory_order_relaxed);
    open_thread_file(t);
    ts_ = t;
    slot = atomic_fetch_add_explicit(&g_nreg, 1, memory_order_relaxed);
    if (slot < MAX_THREADS)
        atomic_store_explicit(&g_reg[slot], (uintptr_t)t, memory_order_release);
    if (g_key_ok) pthread_setspecific(g_key, t);
    return t;
}

NOI static void flush_all(void) {
    unsigned n, i;
    n = atomic_load_explicit(&g_nreg, memory_order_acquire);
    if (n > MAX_THREADS) n = MAX_THREADS;
    for (i = 0; i < n; i++) {
        uintptr_t bits = atomic_load_explicit(&g_reg[i], memory_order_acquire);
        if (!bits) continue;
        flush_claim((struct tstate *)bits);
    }
}

/* ---- signals -------------------------------------------------------- */

NOI static void on_fatal(int sig, siginfo_t *si, void *uc_) {
    static atomic_int in_handler;
    ucontext_t *uc = uc_;
    unsigned char stackbuf[STACK_BYTES];
    uint64_t rip = 0, rsp = 0, addr = 0;
    uint64_t code = 0;
    uint32_t elen = 0;
    size_t got;
    if (atomic_exchange_explicit(&in_handler, 1, memory_order_acq_rel)) {
        signal(sig, SIG_DFL);
        raise(sig);
        return;
    }
    atomic_store_explicit(&g_crashing, 1, memory_order_release);
    if (si) {
        addr = (uint64_t)(uintptr_t)si->si_addr;
        code = (uint64_t)(int64_t)si->si_code;
    }
    if (uc) {
        rip = (uint64_t)uc->uc_mcontext.gregs[REG_RIP];
        rsp = (uint64_t)uc->uc_mcontext.gregs[REG_RSP];
    }
    if (rsp) {
        got = copy_mem(stackbuf, (uintptr_t)rsp, STACK_BYTES);
        if (got == STACK_BYTES) elen = STACK_BYTES;
    }
    if (ts_)
        emit(ts_, (uint8_t)'S', (uint64_t)sig, addr, rip, code,
             elen ? stackbuf : NULL, elen);
    flush_all();
    write_exit_signal(sig);
    write_threads_json();
    signal(sig, SIG_DFL);
    raise(sig);
}

/* ---- hooks ---------------------------------------------------------- */

NOI void __cyg_profile_func_enter(void *fn, void *site) {
    struct tstate *t;
    struct hit h;
    void *fpv;
    uint64_t *fp = NULL;
    uint64_t cfa = 0;
    uint32_t blen;
    volatile uint64_t *slot;
    uint64_t cur;
    if (!atomic_load_explicit(&g_on, memory_order_acquire)) return;
    t = me();
    if (!t) return;
    fpv = __builtin_frame_address(1);
    if (fpv) {
        fp = fpv;
        cfa = (uint64_t)(uintptr_t)fp + 16;
    }
    if (!find_hit((uint64_t)(uintptr_t)fn, &h)) {
        scan_phdrs();
        (void)find_hit((uint64_t)(uintptr_t)fn, &h);
    }
    blen = build_blob(&h, fp != NULL, cfa, t->scratch, sizeof t->scratch);
    emit(t, (uint8_t)'E', (uint64_t)(uintptr_t)fn, (uint64_t)(uintptr_t)site,
         cfa, 0, t->scratch, blen);
    if (!fp) return;
    if (atomic_load_explicit(&g_cet, memory_order_relaxed)) return;
    if (g_no_retval) return;
    if (t->depth >= SHADOW_MAX) return;
    slot = (volatile uint64_t *)(fp + 1);
    cur = *slot;
    if (cur == (uint64_t)(uintptr_t)sensorium_ret_tramp) return;
    t->shadow[t->depth].slot = (uint64_t *)(uintptr_t)(fp + 1);
    t->shadow[t->depth].orig = cur;
    t->shadow[t->depth].rbp = (uint64_t)(uintptr_t)fp;
    t->shadow[t->depth].ret_class = h.found ? h.ret_class : 0;
    t->shadow[t->depth].ret_size = h.found ? h.ret_size : 0;
    t->depth++;
    *slot = (uint64_t)(uintptr_t)sensorium_ret_tramp;
}

NOI void __cyg_profile_func_exit(void *fn, void *site) {
    struct tstate *t;
    if (!atomic_load_explicit(&g_on, memory_order_acquire)) return;
    t = me();
    if (!t) return;
    emit(t, (uint8_t)'X', (uint64_t)(uintptr_t)fn, (uint64_t)(uintptr_t)site,
         0, 0, NULL, 0);
}

NOI __attribute__((used, noinline)) uint64_t
sensorium_ret_hook(uint64_t rax, uint64_t rdx, uint64_t xmm0, uint64_t xmm1) {
    struct tstate *t = ts_;
    uint64_t orig = 0;
    uint8_t cls = 0;
    uint16_t rsz = 0;
    unsigned char mem[256];
    uint32_t elen = 0;
    if (t && t->depth > 0) {
        struct shadow_ent *e = &t->shadow[--t->depth];
        orig = e->orig;
        cls = e->ret_class;
        rsz = e->ret_size;
    }
    if (cls == RET_MEM && rsz > 0 && rax != 0) {
        uint16_t n = rsz > 256 ? 256 : rsz;
        size_t got = copy_mem(mem, (uintptr_t)rax, n);
        if (got) elen = (uint32_t)got;
    }
    if (t && atomic_load_explicit(&g_on, memory_order_relaxed))
        emit(t, (uint8_t)'V', rax, rdx, xmm0, xmm1, elen ? mem : NULL, elen);
    return orig;
}

__asm__(
    ".text\n"
    ".globl sensorium_ret_tramp\n"
    ".type sensorium_ret_tramp,@function\n"
    "sensorium_ret_tramp:\n"
    "  endbr64\n"
    "  sub $48, %rsp\n"
    "  mov %rax, 0(%rsp)\n"
    "  mov %rdx, 8(%rsp)\n"
    "  movq %xmm0, 16(%rsp)\n"
    "  movq %xmm1, 24(%rsp)\n"
    "  mov %rax, %rdi\n"
    "  mov %rdx, %rsi\n"
    "  movq %xmm0, %rdx\n"
    "  movq %xmm1, %rcx\n"
    "  call sensorium_ret_hook\n"
    "  mov %rax, %r11\n"
    "  mov 0(%rsp), %rax\n"
    "  mov 8(%rsp), %rdx\n"
    "  movq 16(%rsp), %xmm0\n"
    "  movq 24(%rsp), %xmm1\n"
    "  add $48, %rsp\n"
    "  jmp *%r11\n"
    ".size sensorium_ret_tramp, .-sensorium_ret_tramp\n"
    ".pushsection .note.GNU-stack,\"\",@progbits\n"
    ".popsection\n");

/* ---- longjmp -------------------------------------------------------- */

NOI static uint64_t demangle_ptr(uint64_t v) {
    uint64_t guard;
    __asm__ volatile("movq %%fs:0x30, %0" : "=r"(guard));
    v = (v >> 17) | (v << (64 - 17));
    return v ^ guard;
}

NOI static void repair_longjmp(struct __jmp_buf_tag *env) {
    struct tstate *t;
    uint64_t rbp, rsp, pc;
    int abandoned = 0;
    uint64_t *jb;
    if (!env) return;
    jb = (uint64_t *)env->__jmpbuf;
    rbp = demangle_ptr(jb[1]);
    rsp = demangle_ptr(jb[6]);
    pc = demangle_ptr(jb[7]);
    t = ts_;
    if (t) {
        /* Stack grows down: abandoned callees have a smaller rbp than
         * the setjmp frame. Leave the setjmp frame itself on the shadow
         * so its later normal return still hits the trampoline once. */
        while (t->depth > 0 && t->shadow[t->depth - 1].rbp < rbp) {
            struct shadow_ent *e = &t->shadow[t->depth - 1];
            if (e->slot) *e->slot = e->orig;
            t->depth--;
            abandoned++;
        }
        emit(t, (uint8_t)'J', rbp, rsp, pc, (uint64_t)abandoned, NULL, 0);
    }
}

/* A fortify header may still have macro-substituted these names. */
#undef longjmp
#undef _longjmp
#undef siglongjmp

NOI __attribute__((noreturn)) void longjmp(struct __jmp_buf_tag env[1], int val) {
    resolve_syms();
    if (atomic_load_explicit(&g_on, memory_order_acquire)) repair_longjmp(env);
    if (real_longjmp) real_longjmp(env, val);
    abort();
}

NOI __attribute__((noreturn)) void _longjmp(struct __jmp_buf_tag env[1], int val) {
    resolve_syms();
    if (atomic_load_explicit(&g_on, memory_order_acquire)) repair_longjmp(env);
    if (real__longjmp) real__longjmp(env, val);
    else if (real_longjmp) real_longjmp(env, val);
    abort();
}

NOI __attribute__((noreturn)) void siglongjmp(sigjmp_buf env, int val) {
    resolve_syms();
    if (atomic_load_explicit(&g_on, memory_order_acquire))
        repair_longjmp((struct __jmp_buf_tag *)env);
    if (real_siglongjmp) real_siglongjmp((struct __jmp_buf_tag *)env, val);
    else if (real_longjmp) real_longjmp((struct __jmp_buf_tag *)env, val);
    abort();
}

NOI __attribute__((noreturn)) void __longjmp_chk(struct __jmp_buf_tag env[1], int val) {
    resolve_syms();
    if (atomic_load_explicit(&g_on, memory_order_acquire)) repair_longjmp(env);
    if (real___longjmp_chk) real___longjmp_chk(env, val);
    else if (real_longjmp) real_longjmp(env, val);
    abort();
}

/* ---- assert --------------------------------------------------------- */

NOI static size_t clip_str(unsigned char *dst, const char *src, size_t cap) {
    size_t i = 0;
    if (!src) return 0;
    while (i < cap && src[i]) {
        dst[i] = (unsigned char)src[i];
        i++;
    }
    return i;
}

NOI __attribute__((noreturn)) void
__assert_fail(const char *assertion, const char *file, unsigned line,
              const char *function) {
    struct tstate *t;
    unsigned char extra[ASSERT_CLIP * 3 + 8];
    size_t n = 0, c;
    resolve_syms();
    if (atomic_load_explicit(&g_on, memory_order_acquire)) {
        t = ts_ ? ts_ : me();
        c = clip_str(extra, assertion, ASSERT_CLIP);
        n = c;
        extra[n++] = 0;
        c = clip_str(extra + n, file, ASSERT_CLIP);
        n += c;
        extra[n++] = 0;
        c = clip_str(extra + n, function, ASSERT_CLIP);
        n += c;
        if (t) {
            emit(t, (uint8_t)'A', (uint64_t)line, 0, 0, 0, extra, (uint32_t)n);
            flush_claim(t);
        }
    }
    if (real_assert_fail) real_assert_fail(assertion, file, line, function);
    abort();
}

/* ---- fork ----------------------------------------------------------- */

NOI static void replay_file(const char *name, const void *buf, size_t n) {
    char path[4200];
    int fd;
    if (!buf || !n) return;
    if (join2(path, sizeof path, g_proc, name) != 0) return;
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0600);
    if (fd < 0) return;
    (void)write_full(fd, buf, n);
    close(fd);
}

NOI static void child_switch(void) {
    pid_t pid = getpid();
    struct tstate *self;
    unsigned n, i;
    if (!atomic_load_explicit(&g_on, memory_order_relaxed)) return;
    if (pid == g_proc_pid) return;
    self = ts_;
    n = atomic_load_explicit(&g_nreg, memory_order_relaxed);
    if (n > MAX_THREADS) n = MAX_THREADS;
    for (i = 0; i < n; i++) {
        uintptr_t bits = atomic_load_explicit(&g_reg[i], memory_order_relaxed);
        struct tstate *t;
        if (!bits) continue;
        t = (struct tstate *)bits;
        if (t->fd >= 0) {
            close(t->fd);
            t->fd = -1;
        }
        if (t != self) {
            atomic_store_explicit(&t->dead, 1, memory_order_relaxed);
            atomic_store_explicit(&g_reg[i], 0, memory_order_relaxed);
        }
    }
    /* Drop the copied buffer. Those bytes were flushed to the parent. */
    if (self) {
        self->len = 0;
        atomic_store_explicit(&self->pub_len, 0, memory_order_relaxed);
        atomic_store_explicit(&self->disk_len, 0, memory_order_relaxed);
    }
    atomic_store_explicit(&g_started, 0, memory_order_relaxed);
    g_nkids = 0;
    if (ensure_dirs(pid) != 0) {
        atomic_store_explicit(&g_on, 0, memory_order_relaxed);
        return;
    }
    write_boot();
    replay_file("argv.json", g_argv_json, g_argv_len);
    replay_file("objs.txt", g_objs_txt, g_objs_len);
    if (self) open_thread_file(self);
}

NOI static void atfork_prepare(void) {
    if (ts_) flush_claim(ts_);
}

NOI static void atfork_parent(void) {}

NOI static void atfork_child(void) { child_switch(); }

NOI pid_t fork(void) {
    pid_t pid;
    struct tstate *t;
    resolve_syms();
    if (!atomic_load_explicit(&g_on, memory_order_acquire) || !real_fork) {
        if (!real_fork) {
            errno = ENOSYS;
            return -1;
        }
        return real_fork();
    }
    t = ts_ ? ts_ : me();
    if (t) flush_claim(t);
    pid = real_fork();
    if (pid == 0) {
        child_switch(); /* idempotent if the atfork child handler ran */
        return 0;
    }
    if (pid > 0) {
        if (g_nkids < (int)(sizeof g_kids / sizeof g_kids[0]))
            g_kids[g_nkids++] = pid;
        write_forks_json();
        if (t) emit(t, (uint8_t)'F', (uint64_t)pid, 0, 0, 0, NULL, 0);
    }
    return pid;
}

/* ---- pthread_create ------------------------------------------------- */

struct start_pack {
    void *(*fn)(void *);
    void *arg;
};

NOI static void *thread_main(void *p) {
    struct start_pack pack = *(struct start_pack *)p;
    free(p);
    if (atomic_load_explicit(&g_on, memory_order_acquire)) (void)me();
    return pack.fn(pack.arg);
}

NOI int pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                       void *(*start)(void *), void *arg) {
    struct start_pack *pack;
    int rc;
    resolve_syms();
    if (!atomic_load_explicit(&g_on, memory_order_acquire) || !real_pthread_create) {
        if (!real_pthread_create) return EAGAIN;
        return real_pthread_create(thread, attr, start, arg);
    }
    pack = malloc(sizeof *pack);
    if (!pack) return EAGAIN;
    pack->fn = start;
    pack->arg = arg;
    rc = real_pthread_create(thread, attr, thread_main, pack);
    if (rc != 0) free(pack);
    return rc;
}

/* ---- startup / shutdown --------------------------------------------- */

NOI static void resolve_syms(void) {
    int exp = 0;
    int st = atomic_load_explicit(&g_resolved, memory_order_acquire);
    if (st == 2) return;
    if (!atomic_compare_exchange_strong_explicit(
            &g_resolved, &exp, 1, memory_order_acq_rel, memory_order_acquire)) {
        while (atomic_load_explicit(&g_resolved, memory_order_acquire) != 2)
            pause_once();
        return;
    }
    real_longjmp = (lj_fn)dlsym(RTLD_NEXT, "longjmp");
    real__longjmp = (lj_fn)dlsym(RTLD_NEXT, "_longjmp");
    real_siglongjmp = (lj_fn)dlsym(RTLD_NEXT, "siglongjmp");
    real___longjmp_chk = (lj_fn)dlsym(RTLD_NEXT, "__longjmp_chk");
    real_assert_fail = (assert_fn)dlsym(RTLD_NEXT, "__assert_fail");
    real_fork = (fork_fn)dlsym(RTLD_NEXT, "fork");
    real_pthread_create = (thr_fn)dlsym(RTLD_NEXT, "pthread_create");
    atomic_store_explicit(&g_resolved, 2, memory_order_release);
}

NOI static void on_exit_fn(int code, void *unused) {
    (void)unused;
    if (!atomic_load_explicit(&g_on, memory_order_relaxed)) return;
    if (atomic_load_explicit(&g_crashing, memory_order_relaxed)) return;
    write_exit_status(code);
}

NOI static void at_exit_fn(void) {
    if (!atomic_load_explicit(&g_on, memory_order_relaxed)) return;
    if (ts_) flush_claim(ts_);
    flush_all();
    write_threads_json();
}

NOI __attribute__((constructor, no_instrument_function)) static void boot(void) {
    const char *root;
    ssize_t n;
    struct sigaction sa;
    int sigs[5];
    unsigned i;
    resolve_syms();
    root = getenv("SENSORIUM_C_ROOT");
    if (!root || !root[0]) return;
    if (strlen(root) >= sizeof g_root) return;
    memcpy(g_root, root, strlen(root) + 1);
    {
        const char *nr = getenv("SENSORIUM_C_NO_RETVAL");
        const char *rv = getenv("SENSORIUM_C_RETVAL");
        if ((nr && nr[0] && strcmp(nr, "0") != 0) || (rv && strcmp(rv, "0") == 0))
            g_no_retval = 1;
    }
    n = readlink("/proc/self/exe", g_exe, sizeof g_exe - 1);
    if (n < 0) n = 0;
    g_exe[n] = 0;
    if (ensure_dirs(getpid()) != 0) return;
    write_argv();
    write_boot();
    cet_check();
    scan_phdrs();
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = on_fatal;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigs[0] = SIGSEGV;
    sigs[1] = SIGABRT;
    sigs[2] = SIGFPE;
    sigs[3] = SIGBUS;
    sigs[4] = SIGILL;
    for (i = 0; i < 5; i++) sigaction(sigs[i], &sa, NULL);
    if (pthread_key_create(&g_key, thread_dead) == 0) g_key_ok = 1;
    pthread_atfork(atfork_prepare, atfork_parent, atfork_child);
    atexit(at_exit_fn);
    on_exit(on_exit_fn, NULL);
    atomic_store_explicit(&g_on, 1, memory_order_release);
    (void)me();
}
