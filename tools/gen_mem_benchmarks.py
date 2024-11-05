#!/usr/bin/env python3
from types import SimpleNamespace
from textwrap import indent, dedent
from typing import Literal, assert_never, get_args
import yaml
from dataclasses import dataclass, fields as get_dataclass_fields
import itertools
import SME


OpEncoding = Literal['reg-adjacent', 'reg-strided', 'za-vector']
MemOperation  = Literal['load', 'store', 'copy']


@dataclass(kw_only=True)
class Benchmark:
  label : str
  encoding: OpEncoding
  feature: str
  op: MemOperation
  # number of VL-sized transfers per instuction
  n_vectors: int
  # element bit width, -1 if untyped
  data_size: int
  ilp: int
  fn: tuple[str, str]

  def to_c_struct(self):
    fields = [f"{{ &setup, &{self.fn[0]}, &teardown }}"]

    for field in get_dataclass_fields(self):
      if field.name == "fn": continue

      val = getattr(self, field.name)
      val = f"\"{val}\"" if isinstance(val, str) else str(val)

      fields.append(val)

    return f"{{{", ".join(fields)}}}"


class LoadStoreEncoder:
  # instruction class encoding
  encoding: OpEncoding
  # max possible ILP per unrolled loop (number of instructions without data dependencies)
  max_independent_instructions: int
  # number of VL-sized vectors transferred per instruction
  n_vectors: int
  # transfer data type, if typed
  data: SME.SMEType | None
  # registers used
  clobber: str

  def emit_prologue(self, asm: SME.AsmBlock): pass

  def emit(self, asm: SME.AsmBlock, op: Literal["load", "store"], base: str, index: int): pass

  def make_description(self, op: MemOperation):
    # operations
    ops = []
    if op in ["load", "copy"]: ops.append(self.opcode("load"))
    if op in ["store", "copy"]: ops.append(self.opcode("store"))

    # encoding-class specific
    size_desc = {1:"one register", 2:"two register", 4:"four register"}

    match self.encoding:
      case "za-vector":
        short = "za[]"
        long = "ZA vector"
      case "reg-adjacent":
        short = f"reg[x{self.n_vectors}, adjacent]" if self.n_vectors > 1 else "reg"
        long = f"{size_desc[self.n_vectors]}, adjacent, predicated" if self.data is not None else "one register, unpredicated"
      case "reg-strided":
        short = f"reg[x{self.n_vectors}, strided]"
        long = f"{size_desc[self.n_vectors]}, strided, predicated"

    short = f"{"+".join(ops)} {short}"
    long = f"{"/".join(op.upper() for op in ops)} ({long})"

    return (short, long)

  def make_function_name(self, op: MemOperation, ilp: int):
    data = f"_{self.data.label}" if self.data is not None else ""

    return f"{op}_{self.encoding.replace("-", "_")}_x{self.n_vectors}_ilp{ilp}"


  def opcode(self, op: Literal['load', 'store']):
    if self.data == None:
      return "ldr" if op == "load" else "str"
    else:
      suffix = "w" if self.data.suffix == "s" else self.data.suffix
      return f"ld1{suffix}" if op == "load" else f"st1{suffix}"

  def __new__(cls, encoding: OpEncoding, data: SME.SMEType | None, vgsize: int):
    match encoding:
      case "reg-adjacent": cls = RegisterLoadStoreEncoder
      case "reg-strided": cls = StridedRegisterLoadStoreEncoder
      case "za-vector": cls = ZALoadStoreEncoder
      case _: assert_never(encoding)

    instance = object.__new__(cls)
    instance.encoding = encoding
    return instance

class ZALoadStoreEncoder(LoadStoreEncoder):
  def __init__(self, encoding: OpEncoding, data: SME.SMEType | None, vgsize: int):
    assert encoding == "za-vector"
    assert data is None, "za array load must be untyped"
    assert vgsize == 1
    self.max_independent_instructions = 16
    self.n_vectors = 1
    self.data = None
    self.predicate = None
    self.clobber = ", \"x12\""

  def emit_prologue(self, asm: SME.AsmBlock):
    asm.emit("mov","x12", "#0")

  def emit(self, asm: SME.AsmBlock, op: Literal["load", "store"],  base: str, index: int):
    assert index < self.max_independent_instructions
    asm.emit(self.opcode(op), f"za[w12, {index}]", f"[{base}, {index}, MUL VL]")


class RegisterLoadStoreEncoder(LoadStoreEncoder):
  def __init__(self, encoding: OpEncoding, data: SME.SMEType | None, vgsize: int):
    assert encoding == "reg-adjacent"
    assert (data is None and vgsize == 1) or data is not None, "multivector load/stores must be typed"
    assert vgsize in [1, 2, 4]
    self.max_independent_instructions = 8
    self.data = data
    self.n_vectors = vgsize
    self.predicate = None
    self.clobber = ""
    if data is not None:
      self.predicate = "p0" if vgsize == 1 else "pn8"

  def emit_prologue(self, asm: SME.AsmBlock):
    if self.predicate is None: return
    asm.emit("ptrue", f"{self.predicate}.{self.data.suffix}")

  def emit(self, asm: SME.AsmBlock, op: Literal["load", "store"],  base: str, index: int):
    assert index < self.max_independent_instructions

    # vector group index range
    i0 = index*self.n_vectors
    i1 = (index+1)*self.n_vectors - 1

    # encode the storage register(s)
    suffix = "" if self.data is None else f".{self.data.suffix}"
    reg = f"z{i0}{suffix}" if i0 == i1 else f"{{z{i0}{suffix}-z{i1}{suffix}}}"

    # predicate encoding differts for load and store
    if self.predicate is not None and op == "load":
      predicate = self.predicate + "/z"
    else:
      predicate = self.predicate

    # emit the instruction
    asm.emit(self.opcode(op), reg, predicate, f"[{base}, {i0}, MUL VL]")

class StridedRegisterLoadStoreEncoder(LoadStoreEncoder):
  def __init__(self, encoding: OpEncoding, data: SME.SMEType | None, vgsize: int):
    assert encoding == "reg-strided"
    assert data is not None
    assert vgsize in [2, 4]
    self.max_independent_instructions = 8
    self.data = data
    self.n_vectors = vgsize
    self.clobber = ""

  def emit_prologue(self, asm: SME.AsmBlock):
    asm.emit("ptrue", f"pn8.{self.data.suffix}")

  def emit(self, asm: SME.AsmBlock, op: Literal["load", "store"],  base: str, index: int):
    assert index < self.max_independent_instructions
    stride = 16//self.n_vectors

    # the initial register has the index 0 <= . < stride or 16 <= . < 16 + stride
    # map the index to that range
    offset = 16*(index // stride) + index % stride

    # strided registers
    regs = ", ".join(f"z{offset + i*stride}.{self.data.suffix}" for i in range(self.n_vectors))
    regs = f"{{{regs}}}"

    # emit the instruction
    asm.emit(self.opcode(op), regs, "pn8/z" if op == "load" else "pn8", f"[{base}, {index*self.n_vectors}, MUL VL]")


def make_benchmark_function(encoder: LoadStoreEncoder, op: MemOperation, ilp: int):
  """ Build benchmarking code for the operation using ilp data-parallel instructions per chunk """
  assert ilp >= 1 and ilp <= encoder.max_independent_instructions

  # bytes processed per instruction and loop iteration
  bytes_per_instruction = encoder.n_vectors*64
  bytes_per_loop = bytes_per_instruction*ilp

  # generate the microbenchmark assembly
  asm = SME.AsmBlock()

  # prologue
  asm.emit("smstart")
  asm.emit("mov", "x0", "%[n]")
  encoder.emit_prologue(asm)

  # data pointers
  if op == "copy":
    ptr = [("x1", "load", "src"), ("x2", "store", "dst")]
  elif op == "load":
    ptr = [("x1", "load", "src")]
  else:
    ptr = [("x1", "store", "dst")]

  # the outer loop (repeat n times)
  with asm.labeled_block(1):
    for (reg, _, addr) in ptr: asm.emit("mov", reg, f"%[{addr}]") # source data pointer

    # We split the processing in two parts: a main loop that uses multiple
    # instructions to process chunk_size bytes per iteration, and a tail
    # loop that processes the rest

    # main loop (ILP=ilp)
    with asm.labeled_block(2):
      # emit intructions
      for (reg, op_type, _) in ptr:
        for i in range(ilp): encoder.emit(asm, op_type, reg, i)
        asm.emit("")

      # increment the pointers
      for (reg, _, _) in ptr: asm.emit("add", reg, reg, f"#{bytes_per_loop}")

      # repeat the loop
      asm.emit("cmp", ptr[0][0], "%[end_aligned]" if ilp > 1 else "%[end]")
      asm.emit("b.lo", "2b")

      if (ilp > 1): asm.emit("b", "4f")

    # tail loop (only needed if ilp > 1)
    if ilp > 1:
      with asm.labeled_block(3):
        # one instruction
        for (reg, op_type, _) in ptr:
          encoder.emit(asm, op_type, reg, 0)
          asm.emit("add", reg, reg, f"#{bytes_per_instruction}")

      # tail loop condition
      with asm.labeled_block(4):
        asm.emit("cmp", ptr[0][0], "%[end]")
        asm.emit("b.lo", "3b")

    # advance the outer loop
    asm.emit("")
    asm.emit("subs", "x0", "x0", "#1")
    asm.emit("b.ne", "1b")

    # asm epilogue
    asm.emit("smstop")


  # asm block inputs
  asm_inputs = f"[n] \"r\" (data->n_iterations), "
  asm_inputs = asm_inputs + ", ".join(f"[{addr}] \"r\" (data->{addr})" for (_, _, addr) in ptr)
  asm_inputs = asm_inputs + f", [end] \"r\" (data->{ptr[0][2]} + data->size)"

  # clobbered registers (x0 counter + pointers)
  clobber = "\"x0\", " + ", ".join(f"\"{reg}\"" for (reg, _, _) in ptr) + encoder.clobber

  # tail computation
  if ilp > 1:
    tail_computation = f"\n      size_t size_aligned = data->size - (data->size % {bytes_per_loop});"
    asm_inputs = asm_inputs + f", [end_aligned] \"r\" (data->{ptr[0][2]} + size_aligned)"
  else:
    tail_computation = ""

  # transfer factor (2.0 if we do a copy)
  factor = "2.0*" if op == "copy" else ""

  # description
  (label, description) = encoder.make_description(op)

  # build the function
  fn_name = encoder.make_function_name(op, ilp)

  fn_body =  dedent(f"""
    static double {fn_name}(const void* args) {{
      // {description}
      //
      // Bytes per instruction: {bytes_per_instruction}, bytes per loop iteration: {bytes_per_loop} (ILP={ilp})
      const benchmark_data_t* data = args;{tail_computation}

      //printf("starting {fn_name}\\n");

      __asm__ __volatile__ (
        {asm.join()}
        : // nothing
        : {asm_inputs}
        : {clobber}
      );

      //printf("done {fn_name}\\n");

      // number of bytes transferred overall
      return {factor}data->total_size;
    }}
  """)

  return Benchmark(
    label = description,
    encoding = encoder.encoding,
    feature = "FEAT_SME2",
    op = op,
    n_vectors= encoder.n_vectors,
    # data size
    data_size = encoder.data.size if encoder.data is not None else -1,
    ilp = ilp,
    fn = (fn_name, fn_body)
  )

# build benchmarks (encoding, data, vgsize)
#
benchmark_params = [
  (["za-vector", "reg-adjacent"], [None], [1]),
  (["reg-adjacent", "reg-strided"], [SME.Types.f32], [2, 4]),
]


benchmarks = []
# ugly nested for
for params in benchmark_params:
  for (encoding, data, vgsize, op_type) in itertools.product(*params, get_args(MemOperation)):
    encoder = LoadStoreEncoder(encoding, data, vgsize)
    for ilp in (i + 1 for i in range(encoder.max_independent_instructions)):
      bench = make_benchmark_function(encoder, op_type, ilp)
      benchmarks.append(bench)



# build the file
print(f"""// generated by tools/gen_mem_benchmarks.py, do not edit!
#include <assert.h>
#include <stdlib.h>
#include "bench.h"

// Allocation granularity, must be large enough to align with 4x multivector load/store
#define SIZE_ALIGNMENT (64*4)

// Benchmark parameters
typedef struct {{
  char*  src;
  char*  dst;
  size_t size;
  size_t n_iterations;
  double total_size;
}} benchmark_data_t;

// Benchmark functions
{"\n".join(bench.fn[1] for bench in benchmarks)}

// benchmark setup
#define MB(x) (size_t)x*1048576UL

static size_t find_n_iterations(size_t size) {{
  // at least 512MB
  size_t n = MB(512)/size;
  n = n < 16 ? 16 : n;
  return n;
}}

static void* setup(const void* args) {{
  const mem_benchmark_params_t* params = args;

  // allocations must be done in steps of SIZE_ALIGNMENT
  assert(params->size % SIZE_ALIGNMENT == 0);

  // at least 16-byte alignment
  assert(params->alignment % {16}UL == 0);

  // allocate buffer for the benchmark
  benchmark_data_t* data = malloc(sizeof(benchmark_data_t));
  data->size = params->size;
  data->src = aligned_alloc(params->alignment, params->size);
  data->dst = aligned_alloc(params->alignment, params->size);
  data->n_iterations = find_n_iterations(data->size);
  data->total_size = (double)data->size*(double)data->n_iterations;

  assert(data->src != nullptr);
  assert(data->dst != nullptr);

  return data;
}}

static void teardown(void* args) {{
  benchmark_data_t* data = args;

  free(data->src); data->src = nullptr;
  free(data->dst); data->src = nullptr;
  free(data);
}}


// benchmark table
static const mem_benchmark_t benchmarks[] = {{
  {",\n  ".join(bench.to_c_struct() for bench in benchmarks)}
}};

CONST_PTR(mem_benchmark_t) mem_benchmarks = benchmarks;
const size_t mem_benchmarks_count = sizeof(benchmarks)/sizeof(benchmarks[0]);
""")
