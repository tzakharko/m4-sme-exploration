#!/usr/bin/env python3
from textwrap import dedent


class AsmBlock:
  """ Simple gcc assembly emitter """  
  def __init__(self, width: int = 60):
    self.width = width
    self.body  = []

  def emit(self, line): 
    line = f"\"{line.ljust(60)}\\n\""
    self.body.append(line)

  def join(self, first_ident = 0, second_ident = 8):
    first = "".ljust(first_ident)
    second = "".ljust(second_ident)

    if len(self.body) == 0:
      return first

    out = first + self.body[0]
    for i in range(1, len(self.body)):
      out = out + "\n" + second + self.body[i]

    return out

def gen_fmla_test(elem: int, vg: int, za: int):
  """ Generate fmla benchmark for given element size and intended block size """
  assert elem in (8, 16, 32, 64), "invalid element size"
  assert vg in (2, 4), "invalid vector group size"
  assert za > 0 and za <= 64, "invalid number of ZA slices"
  assert za % vg == 0, "number of ZA slices must be divisible by the vector group size"

  # number of instructions needed
  n_inst  = za // vg
  # number of base registers
  n_bases = (n_inst - 1) // 8 + 1
  base_regs = ["x{}".format(i + 8) for i in range(n_bases)]
  # number of fma per instruction
  n_fma   = (512 // elem)*vg

  # arm type suffix
  match elem:
    case 8: s = "b"
    case 16: s = "h"
    case 32: s = "s"
    case 64: s = "d"

  # build the assembly body
  asm = AsmBlock()

  # prologue
  asm.emit("mov x0, %[n]")
  for i, reg in enumerate(base_regs):
    asm.emit(f"mov {reg}, #{i*8}")
  asm.emit("smstart")

  # the fmla loop
  asm.emit("1:")
  for i in range(n_inst):
    base   = f"w{i // 8 + 8}"
    offset = i % 8

    # single fmla
    line = f"  fmla za.{s}[{base}, {offset}, VGx{vg}], {{z0.{s}-z{vg-1}.{s}}}, {{z4.{s}-z{vg + 3}.{s}}}"    
    asm.emit(line)

  # loop end
  asm.emit("")
  asm.emit("  subs x0, x0, #1")
  asm.emit("  b.ne  1b")

  # asm epilogue
  asm.emit("smstop")

  # build the function
  fun = f"""
    double sme_fmla_f{elem}_VGx{vg}_{za}(void) {{
      // each FMLA operates on {vg} pairs of {512//elem}-wide fp{elem} registers, multiplies the pairwise 
      // elements and accumulates the results into {vg} ZA tile slices, for the total of {n_fma} FMAs or {n_fma*2} FLOPS"
      //
      // we need {n_inst} FMLA instructions to output {za} ZA tile slices"
      double flops_per_iteration = {n_inst}*{n_fma*2};

      int64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (N_ITERATIONS)
        : "x0", {", ".join((f"\"{r}\"" for r in base_regs))}
      );
      uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

      // compute the rate
      double elapsed = (double)(t1 - t0)/1e9;
      double gflops  = flops_per_iteration*N_ITERATIONS/elapsed/1e9;
  
      return gflops;
    }}
  """
  return dedent(fun)


def gen_fmlal_test(elem: int, vg: int, za: int):
  """ Generate fmlal benchmark for given element size and intended block size """
  assert elem in (8, 16), "invalid element size"
  assert vg in (2, 4), "invalid vector group size"
  assert za > 0 and za <= 64, "invalid number of ZA slices"
  assert za % (vg*2) == 0, "number of ZA slices must be divisible by the double of vector group size"

  # number of instructions needed
  n_inst  = za // (vg*2)
  # number of base registers
  n_bases = (n_inst - 1) // 4 + 1
  base_regs = ["x{}".format(i + 8) for i in range(n_bases)]
  # number of fma per instruction
  n_fma   = (512 // elem)*vg

  # arm type suffix
  match elem:
    case 8: s0, s1 = "b", "h"
    case 16: s0, s1 = "h", "s"

  # build the assembly body
  asm = AsmBlock()

  # prologue
  asm.emit("mov x0, %[n]")
  for i, reg in enumerate(base_regs):
    asm.emit(f"mov {reg}, #{i*8}")
  asm.emit("smstart")

  # the fmlal loop
  asm.emit("1:")
  for i in range(n_inst):
    base   = f"w{i // 4 + 8}"
    offset = (i % 4)*2

    # single fmla
    line = f"  fmlal za.{s1}[{base}, {offset}:{offset + 1}, VGx{vg}], {{z0.{s0}-z{vg-1}.{s0}}}, {{z4.{s0}-z{vg + 3}.{s0}}}"    
    asm.emit(line)

  # loop end
  asm.emit("")
  asm.emit("  subs x0, x0, #1")
  asm.emit("  b.ne  1b")

  # asm epilogue
  asm.emit("smstop")

  # build the function
  fun = f"""
    double sme_fmlal_f{elem}f{elem*2}_VGx{vg}_{za}(void) {{
      // each FMLAL operates on {vg} pairs of {512//elem}-wide fp{elem} registers, widens them to fp{elem*2}, 
      // multiplies the elements pairwise and accumulates the results into {vg*2} ZA tile slices, 
      // for the total of {n_fma} FMAs or {n_fma*2} FLOPS
      //
      // we need {n_inst} FMLA instructions to output {za} ZA tile slices"
      double flops_per_iteration = {n_inst}*{n_fma*2};

      int64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (N_ITERATIONS)
        : "x0", {", ".join((f"\"{r}\"" for r in base_regs))}
      );
      uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

      // compute the rate
      double elapsed = (double)(t1 - t0)/1e9;
      double gflops  = flops_per_iteration*N_ITERATIONS/elapsed/1e9;
  
      return gflops;
    }}
  """
  return dedent(fun)


def gen_fmopa_test(elem: int, tiles: int):
  """ Generate fmopa benchmark for given element size and the number of tiles """
  assert elem in (8, 16, 32, 64), "invalid element size"
  assert tiles > 0 and tiles <= elem, "number of tiles exceeded"

  # number of instructions needed
  n_inst  = tiles
  # number of fma per instruction
  n_fma   = (512/elem)**2

  # arm type suffix
  match elem:
    case 8: s = "b"
    case 16: s = "h"
    case 32: s = "s"
    case 64: s = "d"

  # build the assembly body
  asm = AsmBlock()

  # prologue
  asm.emit("mov x0, %[n]")
  asm.emit("smstart")
  asm.emit(f"ptrue p0.{s}")

  # the fmla loop
  asm.emit("1:")
  for i in range(n_inst):
    # single fmopa
    line = f"  fmopa za{i}.{s}, p0/m, p0/m, z{i*2}.{s}, z{i*2 + 1}.{s}"    
    asm.emit(line)

  # loop end
  asm.emit("")
  asm.emit("  subs x0, x0, #1")
  asm.emit("  b.ne  1b")

  # asm epilogue
  asm.emit("smstop")

  # build the function
  fun = f"""
    double sme_fmopa_f{elem}_{tiles}(void) {{
      // each FMOPA calculates the outer product of two {512//elem}-wide fp{elem} registers and accumulates
      // the results into a {512//elem}x{512//elem} ZA tile, for the total of {n_fma} FMAs or {n_fma*2} FLOPS"
      //
      // we need {n_inst} FMOPA instructions to output {tiles} ZA tiles"
      double flops_per_iteration = {n_inst}*{n_fma*2};

      int64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (N_ITERATIONS)
        : "x0"
      );
      uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

      // compute the rate
      double elapsed = (double)(t1 - t0)/1e9;
      double gflops  = flops_per_iteration*N_ITERATIONS/elapsed/1e9;
  
      return gflops;
    }}
  """
  return dedent(fun)


def gen_fmopa_widening_test(elem: int, accum: int, tiles: int):
  """ Generate fmopa benchmark for given element and accumulator size and the number of tiles """
  assert elem in (8, 16), "invalid element size"
  assert accum in (32, 64), "invalid element size"
  assert tiles > 0 and tiles <= accum, "number of tiles exceeded"

  # number of instructions needed
  n_inst  = tiles
  # number of fma per instruction
  n_fma   = (512/elem)**2

  # arm type suffix
  match elem:
    case 8: s = "b"
    case 16: s = "h"
  match accum:
    case 32: d = "s"
    case 64: d = "d"

  # build the assembly body
  asm = AsmBlock()

  # prologue
  asm.emit("mov x0, %[n]")
  asm.emit("smstart")
  asm.emit(f"ptrue p0.{s}")

  # the fmla loop
  asm.emit("1:")
  for i in range(n_inst):
    # single fmopa
    line = f"  fmopa za{i}.{d}, p0/m, p0/m, z{i*2}.{s}, z{i*2 + 1}.{s}"    
    asm.emit(line)

  # loop end
  asm.emit("")
  asm.emit("  subs x0, x0, #1")
  asm.emit("  b.ne  1b")

  # asm epilogue
  asm.emit("smstop")

  # build the function
  fun = f"""
    double sme_fmopa_f{elem}f{accum}_{tiles}(void) {{
      // each FMOPA calculates the matrix product of {512//accum}x2 matrices contained in two 
      // {512//elem}-wide fp{elem} registers and accumulates the widened result into the {512//elem}x{512//elem} ZA tile,
      // for the total of {n_fma} FMAs or {n_fma*2} FLOPS"
      //
      // widening FMOPA is equivalent to performing dot product and accumulate
      //
      // we need {n_inst} FMOPA instructions to output {tiles} ZA tiles"
      double flops_per_iteration = {n_inst}*{n_fma*2};

      int64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (N_ITERATIONS)
        : "x0"
      );
      uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

      // compute the rate
      double elapsed = (double)(t1 - t0)/1e9;
      double gflops  = flops_per_iteration*N_ITERATIONS/elapsed/1e9;
  
      return gflops;
    }}
  """
  return dedent(fun)


def gen_smopa_test(elem: int, accum: int, tiles: int):
  """ Generate smopa benchmark for given element and accumulator size and the number of tiles """
  assert elem in (8, 16), "invalid element size"
  assert accum in (32, 64), "invalid element size"
  assert tiles > 0 and tiles <= accum, "number of tiles exceeded"

  # number of instructions needed
  n_inst  = tiles
  # number of fma per instruction
  n_fma   = (512/elem)**2

  # arm type suffix
  match elem:
    case 8: s = "b"
    case 16: s = "h"
  match accum:
    case 32: d = "s"
    case 64: d = "d"

  # build the assembly body
  asm = AsmBlock()

  # prologue
  asm.emit("mov x0, %[n]")
  asm.emit("smstart")
  asm.emit(f"ptrue p0.{s}")

  # the fmla loop
  asm.emit("1:")
  for i in range(n_inst):
    # single fmopa
    line = f"  smopa za{i}.{d}, p0/m, p0/m, z{i*2}.{s}, z{i*2 + 1}.{s}"    
    asm.emit(line)

  # loop end
  asm.emit("")
  asm.emit("  subs x0, x0, #1")
  asm.emit("  b.ne  1b")

  # asm epilogue
  asm.emit("smstop")

  # build the function
  fun = f"""
    double sme_smopa_i{elem}i{accum}_{tiles}(void) {{
      // each SMOPA calculates the matrix product of {512//accum}x2 matrices contained in two 
      // {512//elem}-wide i{elem} registers and accumulates the widened result into the {512//elem}x{512//elem} ZA tile,
      // for the total of {n_fma} FMAs or {n_fma*2} FLOPS (technically integer ops)"
      //
      // widening SMOPA is equivalent to performing dot product and accumulate
      //
      // we need {n_inst} SMOPA instructions to output {tiles} ZA tiles"
      double flops_per_iteration = {n_inst}*{n_fma*2};

      int64_t t0 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);
      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (N_ITERATIONS)
        : "x0"
      );
      uint64_t t1 = clock_gettime_nsec_np(CLOCK_UPTIME_RAW);

      // compute the rate
      double elapsed = (double)(t1 - t0)/1e9;
      double gflops  = flops_per_iteration*N_ITERATIONS/elapsed/1e9;
  
      return gflops;
    }}
  """
  return dedent(fun)  

# print(gen_smopa_test(8, 32, 4))

# exit()

# build the file
print(f"""
// generated by tools/gen_tests.py, do not edit!

#include <time.h>
#include "sme.h"

static const size_t N_ITERATIONS = 100000000;

// Estimate peak fused multiply and accumulate to ZA rates
{"".join(gen_fmla_test(32, 4, za) for za in range(64, 0, -4))}
{"".join(gen_fmla_test(32, 2, za) for za in range(64, 0, -2))}
{"".join(gen_fmla_test(64, 4, za) for za in range(64, 0, -4))}
{"".join(gen_fmla_test(64, 2, za) for za in range(64, 0, -2))}
{"".join(gen_fmlal_test(16, 4, za) for za in range(64, 0, -8))}
{"".join(gen_fmlal_test(16, 2, za) for za in range(64, 0, -4))}

// Estimate peak outer product to ZA rates
{"".join(gen_fmopa_test(32, tiles) for tiles in range(4, 0, -1))}
{"".join(gen_fmopa_test(64, tiles) for tiles in range(8, 0, -1))}
{"".join(gen_fmopa_widening_test(16, 32, tiles) for tiles in range(4, 0, -1))}
{"".join(gen_smopa_test(16, 32, tiles) for tiles in range(4, 0, -1))}
{"".join(gen_smopa_test(8, 32, tiles) for tiles in range(4, 0, -1))}
""")




# print("// generated by tools/gen_tests.py, do not edit!")
# print("")
# print("#include )


#test(15)