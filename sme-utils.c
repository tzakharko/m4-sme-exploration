#include  <sys/sysctl.h>
#include "sme.h"


size_t sme_vector_length(void) {
  size_t vl;
  
  __asm__ __volatile__ (
    "smstart          \n"
    "rdvl %[vl], #1   \n"
    "smstop           \n"
    : [vl] "=r" (vl)
  );
  
  return vl;
}


bool supports_hw_feature(const char* name) {
  int64_t ret = 0;
  size_t size = sizeof(ret);
  
  if (sysctlbyname(name, &ret, &size, NULL, 0) == -1) {
    return 0;
  }
      
  return ret == 1;
}
