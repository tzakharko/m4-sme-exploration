#!/usr/bin/env python3
from types import SimpleNamespace
from textwrap import indent, dedent
from typing import Literal, assert_never
import yaml
from dataclasses import dataclass, fields as get_dataclass_fields
import SME

# SVE/SME operation encoding (data is in benchmarks.yaml)
OperationEncoding = Literal["za-tile", "za-vector", "za-double-vector", "za-quad-vector", "z-register"]

@dataclass(kw_only=True)
class Operation:
  """ An SVE/SME operation with two register inputs and an output

      See operations.yaml for more info
  """
  @dataclass
  class Output:
    type: OperationEncoding
    data: SME.SMEType

  @dataclass
  class Input:
    data: SME.SMEType

  # fields
  label: str
  category: str
  opcode: str
  feature: str
  predicated: bool
  vgsize: int
  output: Output
  input: Input
  ops: int

  @classmethod
  def from_yaml(cls, yaml):
    return Operation(
      label = yaml.get("label"),
      category = yaml.get("category"),
      opcode = yaml.get("opcode"),
      feature = yaml.get("feature"),
      predicated = yaml.get("predicated", False),
      vgsize = yaml.get("vgsize"),
      output = cls.Output(
        type = yaml.get("output").get("type"),
        data = SME.Types.with_label(yaml.get("output").get("data"))
      ),
      input = cls.Input(
        data = SME.Types.with_label(yaml.get("input").get("data"))
      ),
      ops = yaml.get("ops")
    )

# output encoders for instructions
class OutputEncoder:
  # encoded operations
  op: Operation
  # number of VL-sized vectors of output per instruction
  n_vectors: int
  # number of elements (data lanes) of output per instruction
  n_elements: int
  #  max possible ILP per unrolled loop (number of instructions without data dependencies)
  max_independent_instructions: int

  def encode(self, index: int): pass
  def emit_prologue(self, asm: SME.AsmBlock): pass

  def __new__(cls, op: Operation):
    match op.output.type:
      case "za-tile": cls = ZATileOutputEncoder
      case "za-vector" | "za-double-vector" | "za-quad-vector": cls = ZAVectorOutputEncoder
      case "z-register": cls = RegisterOutputEncoder
      case _ : assert_never(op.output.type)

    return object.__new__(cls)

class ZATileOutputEncoder(OutputEncoder):
  """ Instruction encoder for tile output (e.g. ZA0.S) """
  def __init__(self, op: Operation):
    assert op.output.type == "za-tile"
    self.op = op
    self.n_vectors = 512//op.output.data.size
    self.max_independent_instructions = op.output.data.max_za_tiles
    self.n_elements = self.n_vectors*self.n_vectors
    self.clobber = ""

  def encode(self, index: int):
    assert index >= 0 and index < self.max_independent_instructions
    predicate = ", p0/m, p1/m" if self.op.predicated else ""
    return f"za{index}.{self.op.output.data.suffix}{predicate}"

  def emit_prologue(self, asm: SME.AsmBlock):
    if not self.op.predicated: return
    asm.emit("ptrue", f"p0.{self.op.output.data.suffix}")
    asm.emit("ptrue", f"p1.{self.op.output.data.suffix}")


class ZAVectorOutputEncoder(OutputEncoder):
  """ Instruction encoder for ZA vector output

      - Single-vector, e.g. ZA0.S[w8, 0]
      - Double-vector, e.g. ZA0.S[w8, 0:1]
      - Quad-vector, e.g. ZA0.S[w8, 0:3]

      For vgsize>1, multiple vectors are produced with a stride NRows/vgsize (NRows being the
      number of ZA rows, NRows = VL/8). For example, ZA0.S[w8, 3, VGx2] will output two ZA array
      slices, one at index w8+3 and one at index w8+3 + NRows/vgsize (all indice are  modulo NRows
      to avoid out-of bounds acccess)
  """
  def __init__(self, op: Operation):
    encodings = ["za-vector", "za-double-vector", "za-quad-vector"]
    assert op.output.type in encodings
    assert not op.predicated, "za-vector ouput cannot be predicated"
    self.op = op
    # number of VL-sized vectors of output
    self.n_vectors = int(op.vgsize*2**encodings.index(op.output.type))
    # we only support up to 32 unique indices on VL=512 due to base register limitations
    self.max_independent_instructions = min(64//self.n_vectors, 32)
    self.n_elements = (512//op.output.data.size)*self.n_vectors
    self.clobber = ", \"x8\", \"x9\", \"x10\", \"x11\""

  def encode(self, index: int):
    assert index >= 0 and index < self.max_independent_instructions
    # offset is in range 0..7, select an appropriate base register w8..w11
    if self.op.output.type == "za-vector":
      base   = f"w{index // 8 + 8}"
      offset = str(index % 8)
    elif self.op.output.type == "za-double-vector":
      base   = f"w{index // 4 + 8}"
      offset = (index % 4)*2
      offset = f"{offset}:{offset+1}"
    elif self.op.output.type == "za-quad-vector":
      base   = f"w{index // 2 + 8}"
      offset = (index % 2)*4
      offset = f"{offset}:{offset+3}"

    vgsize = f", VGx{self.op.vgsize}" if self.op.vgsize > 1 else ""

    return f"za.{self.op.output.data.suffix}[{base}, {offset}{vgsize}]"

  def emit_prologue(self, asm: SME.AsmBlock):
    # init the base registers
    for i in range(4): asm.emit("mov", f"x{i + 8}", i*8)


class RegisterOutputEncoder(OutputEncoder):
  """ Instruction encoder for Z register output, e.g Z13.S """
  def __init__(self, op: Operation):
    assert op.output.type == "z-register"
    assert op.vgsize == 1, "Z register output does not support multivectors"
    self.op = op
    self.n_vectors = 1
    self.max_independent_instructions = 32
    self.n_elements = 512//op.output.data.size
    self.clobber = ""

  def encode(self, index: int):
    assert index >= 0 and index < self.max_independent_instructions
    predicate = ", p0/m" if self.op.predicated else ""
    return f"z{index}.{self.op.output.data.suffix}{predicate}"

  def emit_prologue(self, asm: SME.AsmBlock):
    if not self.op.predicated: return
    asm.emit("ptrue", f"p0.{self.op.output.data.suffix}")

# Instruction input encoding
class InputEncoder:
  """ Instruction encoder for register input, e.g z0.s or  {z0.s-z1.s} """
  def __init__(self, op: Operation):
    self.op = op
    self.n_vectors = op.vgsize
    self.n_elements = (512//op.input.data.size)*op.vgsize

  def encode(self, index: int):
    suffix = self.op.input.data.suffix
    vgsize = self.op.vgsize

    # clamp the index to the valid range — this is safe, since we don't write to
    # registers when vgsize == 1
    index = (index % 32//vgsize)

    if vgsize == 1:
      return f"z{index}.{suffix}"
    else:
     return f"{{z{index*vgsize}.{suffix}-z{index*vgsize + vgsize - 1}.{suffix}}}"


# Microbenchmarks
#
# Multiple versions are generated for each operation for varying ILP
@dataclass(kw_only=True)
class Benchmark:
  category: str
  label: str
  feature: str
  encoding: str
  opcode: str
  output_data: str
  output_elements: int
  output_vectors: int
  input_data: str
  input_elements: int
  input_vectors: int
  ops_per_instruction: int
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


def make_benchmark_function_name(op: Operation, ilp: int):
  # vector group size
  za = "_za" if op.output.type.startswith("za") else ""
  vgsize = f"_vgx{op.vgsize}" if op.vgsize > 1 else ""

  return f"{op.opcode}{za}_{op.output.data.label}_{op.input.data.label}{vgsize}_ilp{ilp}"


def make_benchmark_function(op: Operation, ilp: int):
  """ Build benchmarking code for the operation using ilp data-parallel instructions per chunk """
  output_encoder = OutputEncoder(op)
  input_encoder = InputEncoder(op)

  # generate the microbenchmark assembly
  asm = SME.AsmBlock()

  # prologue
  asm.emit("smstart")
  asm.emit("mov", "x0", "%[n]")
  output_encoder.emit_prologue(asm)

  # the microbencmark loop
  with asm.labeled_block(1):
    for i in range(ilp):
      asm.emit(op.opcode, output_encoder.encode(i), input_encoder.encode(i), input_encoder.encode(i))

    asm.emit("")
    asm.emit("subs", "x0", "x0", "#1")
    asm.emit("b.ne", "1b")

  # asm epilogue
  asm.emit("smstop")

  # function declaration
  fn_name = make_benchmark_function_name(op, ilp)
  iters = "N_ITERATIONS" if ilp == 1 else f"N_ITERATIONS/{ilp}"
  ops = op.ops*output_encoder.n_elements


  input_data = f"{input_encoder.n_elements}x {op.input.data.label}"
  output_data = f"{output_encoder.n_elements}x {op.output.data.label}"

  fn_body =  dedent(f"""
    static double {fn_name}(const void*) {{
      // {op.label}, {op.category}
      //
      // Each instruction: ({input_data}, {input_data}) → {output_data} ({ops} OPs)
      // Total of {ops*ilp} OPs per loop iteration, ILP = {ilp}
      size_t n_iterations = {iters};

      __asm__ __volatile__ (
        {asm.join()}
        : // no outputs
        : [n] \"r\" (n_iterations)
        : "x0"{output_encoder.clobber}
      );

      // number of OPS executed (ops_per_instruction*ILP*iterations)
      return {ops}.0*{ilp}.0*(double)n_iterations;
    }}
  """)

  # benchmark definition
  return Benchmark(
    category = op.category,
    label = op.label,
    feature = op.feature,
    encoding = op.output.type,
    opcode = op.opcode,
    output_data = op.output.data.label,
    output_elements = output_encoder.n_elements,
    output_vectors = output_encoder.n_vectors,
    input_data = op.input.data.label,
    input_elements = input_encoder.n_elements*2,
    input_vectors = input_encoder.n_vectors*2,
    ops_per_instruction = ops,
    ilp = ilp,
    fn = (fn_name, fn_body)
  )


# load instruction definitions
with open('benchmarks.yaml', 'r') as file:
    operations = [Operation.from_yaml(y) for y in yaml.safe_load(file)]
    operations.sort(key = lambda op: op.category)

# build benchmarks
benchmarks = []
for op in operations:
  # maximal number of data-independent instructions to emit (limit to 8)
  max_ilp = min(OutputEncoder(op).max_independent_instructions, 16)
  for ilp in  range(1, max_ilp + 1):
    benchmarks.append(make_benchmark_function(op, ilp))

# generate the C code
print(f"""// generated by tools/gen_op_benchmarks.py, do not edit!
#include <assert.h>
#include "bench.h"

// Number of iterations
static const size_t N_ITERATIONS = 8000000;

// benchmark functions
{"\n".join(bench.fn[1] for bench in benchmarks)}

// benchmark setup
static void* setup(const void* params) {{
  assert(params == nullptr);
  return nullptr;
}}

static void teardown(void* data) {{
  assert(data == nullptr);
}}

// benchmark table
static const op_benchmark_t benchmarks[] = {{
  {",\n  ".join(bench.to_c_struct() for bench in benchmarks)}
}};

CONST_PTR(op_benchmark_t) op_benchmarks = benchmarks;
const size_t op_benchmarks_count = sizeof(benchmarks)/sizeof(benchmarks[0]);
""")
