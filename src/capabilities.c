#include <sys/sysctl.h>

// Return the SVE VL in streaming mode
size_t get_sme_vector_length(void) {
  size_t vl;

  __asm__ __volatile__ (
    "smstart          \n"
    "rdvl %[vl], #1   \n"
    "smstop           \n"
    : [vl] "=r" (vl)
  );

  return vl;
}

// Query a kernel (sysctl) string, used for feature and system configuration checks
int64_t sysctl_get_int(const char* name) {
  int64_t ret = 0;
  size_t size = sizeof(ret);

  if (sysctlbyname(name, &ret, &size, NULL, 0) == -1) {
    return 0;
  }

  return ret;
}
