#include "benchmarks/bench.h"

// Query a kernel (sysctl) string, used for feature and system configuration checks
int64_t sysctl_get_int(const char* _Nonnull name);

// SVE streaming mode vector size in bytes (SVL)
size_t get_sme_vector_length(void);
