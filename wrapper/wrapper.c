#include <stdio.h>
#include <dlfcn.h>

#define APITRACE_LIB "/data/local/tmp/egltrace.so"

#undef API_ENTRY
#define API_ENTRY(_api) FUNC##_api,

enum API_OFFSET {
    #include API_ENTRIES
    API_NUM
};

static void *func_ptr[API_NUM];

#undef API_ENTRY
#define API_ENTRY(_api)                                 \
    func_ptr[FUNC##_api] = dlsym(lib_handle, #_api);

static void *lib_handle;

void *find_symbol(int offset) {
    if (!lib_handle) {
        lib_handle = dlopen(APITRACE_LIB, RTLD_LOCAL|RTLD_NOW);
#include API_ENTRIES
    }
    return func_ptr[offset];
}

#undef API_ENTRY
#define API_ENTRY(_api)                                            \
    __attribute__((naked)) void _api() {                           \
        asm volatile(                                              \
            "push {r0-r3,lr}\n"                                    \
        );                                                         \
        asm volatile(                                              \
            "mov    r0, %[offset]\n"                               \
            "bl     find_symbol  \n"                               \
            "mov    r12, r0      \n"                               \
            "pop    {r0-r3,lr}\n"                                  \
            "cmp    r12, #0      \n"                               \
            "bxne   r12          \n"                               \
            "mov    r0, #0       \n"                               \
            "bx     lr           \n"                               \
            :                                                      \
            : [offset] "i"(FUNC##_api)                             \
            : "r0", "r1", "r2", "r3", "r12"                        \
            );                                                     \
    }
#include API_ENTRIES
#undef API_ENTRY
